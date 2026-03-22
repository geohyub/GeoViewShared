"""
QC MBES (Multibeam Echo Sounder) Domain Adapter
=================================================
Provides unified QCResult interface for MBES quality control.

Usage:
    from geoview_common.qc.mbes import analyze_mbes_survey
    from geoview_common.qc.mbes.scoring import compute_mbes_score

Copyright (c) 2025-2026 Geoview Co., Ltd.
"""

from __future__ import annotations

from typing import Any, Optional

from ..common.models import (
    QCDomain, QCStatus, QCMetric, QCIssue,
    QCStageResult, QCResult,
)
from ..common.scoring import compute_score, MBES_SCORING_PROFILE


def analyze_mbes_survey(
    survey_data: Any,
    file_name: str = "",
    line_name: str = "",
) -> QCResult:
    """Run MBES QC analysis on survey data and return unified QCResult.

    Args:
        survey_data: MBES survey data object with coverage, crossline,
            SVP, motion, and vessel configuration results.
        file_name: Source file name.
        line_name: Survey line identifier.

    Returns:
        QCResult with stages for coverage, crossline, svp, motion, vessel_config.
    """
    import time
    t0 = time.perf_counter()
    stages = []
    measurements = {}

    # Stage 1: Coverage
    try:
        cov_pct = getattr(survey_data, "coverage_pct", None)
        if cov_pct is not None:
            measurements["coverage_pct"] = cov_pct
            status = QCStatus.PASS if cov_pct >= 95 else (
                QCStatus.WARN if cov_pct >= 80 else QCStatus.FAIL
            )
            stages.append(QCStageResult(
                stage_name="Coverage", stage_index=0,
                score=25 * min(1, cov_pct / 100), max_score=25,
                status=status,
                metrics=[QCMetric("Coverage", cov_pct, "%", status)],
            ))
    except Exception as e:
        stages.append(QCStageResult(
            stage_name="Coverage", stage_index=0, status=QCStatus.NA,
            issues=[QCIssue("warning", "coverage", str(e))],
        ))

    # Stage 2: Crossline Agreement
    try:
        xline_std = getattr(survey_data, "crossline_std_m", None)
        if xline_std is not None:
            measurements["crossline_std_m"] = xline_std
            status = QCStatus.PASS if xline_std <= 0.3 else (
                QCStatus.WARN if xline_std <= 0.6 else QCStatus.FAIL
            )
            stages.append(QCStageResult(
                stage_name="Crossline", stage_index=1,
                score=20 * max(0, 1 - xline_std), max_score=20,
                status=status,
                metrics=[QCMetric("Crossline Std", xline_std, "m", status)],
            ))
    except Exception as e:
        stages.append(QCStageResult(
            stage_name="Crossline", stage_index=1, status=QCStatus.NA,
            issues=[QCIssue("warning", "crossline", str(e))],
        ))

    # Stage 3: SVP (Sound Velocity Profile)
    try:
        svp_res = getattr(survey_data, "svp_residual_ms", None)
        if svp_res is not None:
            measurements["svp_residual_ms"] = svp_res
            status = QCStatus.PASS if svp_res <= 1.0 else (
                QCStatus.WARN if svp_res <= 3.0 else QCStatus.FAIL
            )
            stages.append(QCStageResult(
                stage_name="SVP", stage_index=2,
                score=20 * max(0, 1 - svp_res / 5), max_score=20,
                status=status,
                metrics=[QCMetric("SVP Residual", svp_res, "m/s", status)],
            ))
    except Exception as e:
        stages.append(QCStageResult(
            stage_name="SVP", stage_index=2, status=QCStatus.NA,
            issues=[QCIssue("warning", "svp", str(e))],
        ))

    # Stage 4: Motion Sensor
    try:
        motion_res = getattr(survey_data, "motion_residual_deg", None)
        if motion_res is not None:
            measurements["motion_residual_deg"] = motion_res
            status = QCStatus.PASS if motion_res <= 0.5 else (
                QCStatus.WARN if motion_res <= 1.0 else QCStatus.FAIL
            )
            stages.append(QCStageResult(
                stage_name="Motion", stage_index=3,
                score=20 * max(0, 1 - motion_res / 2), max_score=20,
                status=status,
                metrics=[QCMetric("Motion Residual", motion_res, "deg", status)],
            ))
    except Exception as e:
        stages.append(QCStageResult(
            stage_name="Motion", stage_index=3, status=QCStatus.NA,
            issues=[QCIssue("warning", "motion", str(e))],
        ))

    # Stage 5: Vessel Configuration
    try:
        vc_score = getattr(survey_data, "vessel_config_score", None)
        if vc_score is not None:
            measurements["vessel_config_score"] = vc_score
            status = QCStatus.PASS if vc_score >= 90 else (
                QCStatus.WARN if vc_score >= 50 else QCStatus.FAIL
            )
            stages.append(QCStageResult(
                stage_name="Vessel Config", stage_index=4,
                score=15 * min(1, vc_score / 100), max_score=15,
                status=status,
                metrics=[QCMetric("Config Score", vc_score, "", status)],
            ))
    except Exception as e:
        stages.append(QCStageResult(
            stage_name="Vessel Config", stage_index=4, status=QCStatus.NA,
            issues=[QCIssue("warning", "vessel_config", str(e))],
        ))

    duration = (time.perf_counter() - t0) * 1000

    # Compute unified score
    score_result = compute_score(MBES_SCORING_PROFILE, measurements)

    # Collect issues
    issues = []
    for stage in stages:
        issues.extend(stage.issues)
        if stage.status == QCStatus.FAIL:
            issues.append(QCIssue(
                "critical", stage.stage_name.lower(),
                f"{stage.stage_name} failed",
            ))

    return QCResult(
        domain=QCDomain.MBES,
        file_name=file_name,
        line_name=line_name,
        total_score=score_result["total_score"],
        grade=score_result["grade"],
        status=score_result["status"],
        stages=stages,
        issues=issues,
        duration_ms=duration,
    )
