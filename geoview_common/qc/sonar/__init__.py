"""
QC Sonar (SSS) Domain Adapter
==============================
Wraps SonarQC analysis modules to produce unified QCResult objects.
Imports from original SonarQC package — does NOT duplicate logic.

Usage:
    from geoview_common.qc.sonar import analyze_sonar_project

Copyright (c) 2025-2026 Geoview Co., Ltd.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Optional

from ..common.models import (
    QCDomain, QCStatus, QCMetric, QCIssue,
    QCStageResult, QCResult,
)
from ..common.scoring import compute_score, SONAR_SCORING_PROFILE


def _ensure_sonarqc_importable():
    """Add SonarQC to sys.path if not already importable."""
    sonarqc_paths = [
        Path(r"E:\Software\SonarQC"),
        Path(__file__).resolve().parents[4] / "SonarQC",
    ]
    for p in sonarqc_paths:
        if p.exists() and str(p) not in sys.path:
            sys.path.insert(0, str(p))
            return True
    return False


def analyze_sonar_line(
    line_data: Any,
    range_per_side: float = 200.0,
    altitude_min_pct: float = 10.0,
    altitude_max_pct: float = 20.0,
    grid_resolution: float = 5.0,
    file_name: str = "",
    line_name: str = "",
) -> QCResult:
    """Run SSS QC analysis on a survey line and return unified QCResult.

    Args:
        line_data: SonarQC LineData or LineGroup object.
        range_per_side: Sonar range per side (m).
        altitude_min_pct: Min altitude as % of range.
        altitude_max_pct: Max altitude as % of range.
        grid_resolution: Coverage grid cell size (m).
        file_name: Source file name.
        line_name: Survey line identifier.

    Returns:
        QCResult with stages for altitude, coverage, noise, trackline, location.
    """
    _ensure_sonarqc_importable()

    try:
        from sonarqc.analysis.altitude import analyze_altitude
        from sonarqc.analysis.noise import analyze_noise
        from sonarqc.analysis.trackline import analyze_trackline
        from sonarqc.analysis.location import analyze_location
    except ImportError:
        return QCResult(
            domain=QCDomain.SONAR,
            file_name=file_name,
            line_name=line_name,
            status=QCStatus.NA,
            issues=[QCIssue("critical", "import", "SonarQC package not found")],
        )

    import time
    t0 = time.perf_counter()
    stages = []
    measurements = {}

    # Stage 1: Altitude
    try:
        alt_result = analyze_altitude(
            line_data, range_per_side, altitude_min_pct, altitude_max_pct
        )
        compliance = getattr(alt_result, "compliance_rate", 0)
        measurements["altitude_compliance"] = compliance
        alt_status = QCStatus.PASS if compliance >= 90 else (QCStatus.WARN if compliance >= 70 else QCStatus.FAIL)
        stages.append(QCStageResult(
            stage_name="Altitude",
            stage_index=0,
            score=20 * min(1, compliance / 100),
            max_score=20,
            status=alt_status,
            metrics=[
                QCMetric("Compliance", compliance, "%", alt_status),
                QCMetric("Mean Altitude", getattr(alt_result, "mean_altitude", 0), "m"),
            ],
        ))
    except Exception as e:
        stages.append(QCStageResult(
            stage_name="Altitude", stage_index=0, status=QCStatus.NA,
            issues=[QCIssue("warning", "altitude", str(e))],
        ))

    # Stage 2: Noise
    try:
        noise_result = analyze_noise(line_data, range_per_side)
        noise_score = getattr(noise_result, "quality_score", 50)
        snr = getattr(noise_result, "overall_snr_db", 0)
        measurements["noise_score"] = noise_score
        measurements["snr_db"] = snr
        n_status = QCStatus.PASS if noise_score >= 60 else QCStatus.FAIL
        stages.append(QCStageResult(
            stage_name="Noise",
            stage_index=1,
            score=15 * min(1, noise_score / 100),
            max_score=15,
            status=n_status,
            metrics=[
                QCMetric("Noise Score", noise_score, "", n_status),
                QCMetric("SNR", snr, "dB"),
            ],
        ))
    except Exception as e:
        stages.append(QCStageResult(
            stage_name="Noise", stage_index=1, status=QCStatus.NA,
            issues=[QCIssue("warning", "noise", str(e))],
        ))

    # Stage 3: Trackline
    try:
        track_result = analyze_trackline(line_data)
        straightness = getattr(track_result, "straightness_pct", 50)
        measurements["trackline_straightness"] = straightness
        t_status = QCStatus.PASS if straightness >= 90 else (QCStatus.WARN if straightness >= 50 else QCStatus.FAIL)
        stages.append(QCStageResult(
            stage_name="Trackline",
            stage_index=2,
            score=15 * min(1, straightness / 100),
            max_score=15,
            status=t_status,
            metrics=[
                QCMetric("Straightness", straightness, "%", t_status),
                QCMetric("RMS Deviation", getattr(track_result, "rms_deviation_m", 0), "m"),
            ],
        ))
    except Exception as e:
        stages.append(QCStageResult(
            stage_name="Trackline", stage_index=2, status=QCStatus.NA,
            issues=[QCIssue("warning", "trackline", str(e))],
        ))

    # Stage 4: Location
    try:
        loc_result = analyze_location(line_data)
        fix_rate = getattr(loc_result, "fix_rate", 0)
        measurements["location_fix_rate"] = fix_rate
        l_status = QCStatus.PASS if fix_rate >= 95 else (QCStatus.WARN if fix_rate >= 85 else QCStatus.FAIL)
        stages.append(QCStageResult(
            stage_name="Location",
            stage_index=3,
            score=15 * min(1, fix_rate / 100),
            max_score=15,
            status=l_status,
            metrics=[
                QCMetric("Fix Rate", fix_rate, "%", l_status),
            ],
        ))
    except Exception as e:
        stages.append(QCStageResult(
            stage_name="Location", stage_index=3, status=QCStatus.NA,
            issues=[QCIssue("warning", "location", str(e))],
        ))

    duration = (time.perf_counter() - t0) * 1000

    # Compute unified score
    score_result = compute_score(SONAR_SCORING_PROFILE, measurements)

    # Build issues from stages
    issues = []
    for stage in stages:
        issues.extend(stage.issues)
        if stage.status == QCStatus.FAIL:
            issues.append(QCIssue("critical", stage.stage_name.lower(),
                                   f"{stage.stage_name} failed"))

    return QCResult(
        domain=QCDomain.SONAR,
        file_name=file_name,
        line_name=line_name,
        total_score=score_result["total_score"],
        grade=score_result["grade"],
        status=score_result["status"],
        stages=stages,
        issues=issues,
        duration_ms=duration,
    )
