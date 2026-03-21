"""
QC Seismic Domain Adapter
==========================
Wraps SeismicQC Suite's analysis engine to produce unified QCResult objects.
Imports from original SeismicQC_Suite package — does NOT duplicate logic.

Usage:
    from geoview_common.qc.seismic import analyze_segy_file

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
from ..common.scoring import compute_score, SEISMIC_SCORING_PROFILE


def _ensure_seismicqc_importable():
    """Add SeismicQC_Suite to sys.path if not already importable."""
    seismic_paths = [
        Path(r"E:\Software\SeismicQC_Suite"),
        Path(__file__).resolve().parents[4] / "SeismicQC_Suite",
    ]
    for p in seismic_paths:
        if p.exists() and str(p) not in sys.path:
            sys.path.insert(0, str(p))
            return True
    return False


# Stage name mapping from SeismicQC engine
_STAGE_NAMES = [
    "File Info", "System Detection", "Seafloor Detection",
    "Penetration Analysis", "Navigation", "Signal Quality",
    "Spectrum Analysis", "Data Integrity", "Anomaly Detection", "Scoring",
]


def analyze_segy_file(
    file_path: str | Path,
    max_traces: int = 2000,
    file_name: str = "",
) -> QCResult:
    """Run SeismicQC 10-stage pipeline on a SEG-Y file.

    Args:
        file_path: Path to SEG-Y file.
        max_traces: Max traces to sample (default 2000 for performance).
        file_name: Display name (defaults to file_path stem).

    Returns:
        QCResult with 10 pipeline stages.
    """
    _ensure_seismicqc_importable()

    file_path = Path(file_path)
    if not file_name:
        file_name = file_path.name

    try:
        from analysis.engine import QCEngine
        from core.segy_reader import read_segy_info
    except ImportError:
        return QCResult(
            domain=QCDomain.SEISMIC,
            file_name=file_name,
            status=QCStatus.NA,
            issues=[QCIssue("critical", "import", "SeismicQC_Suite not found")],
        )

    import time
    t0 = time.perf_counter()

    # Run the native 10-stage pipeline
    try:
        engine = QCEngine(max_traces=max_traces)
        native_result = engine.run(str(file_path))
    except Exception as e:
        return QCResult(
            domain=QCDomain.SEISMIC,
            file_name=file_name,
            status=QCStatus.FAIL,
            issues=[QCIssue("critical", "engine", f"QCEngine failed: {e}")],
            duration_ms=(time.perf_counter() - t0) * 1000,
        )

    duration = (time.perf_counter() - t0) * 1000

    # Convert native result to unified QCResult
    stages = []
    measurements = {}

    # Map native stage results to QCStageResult
    if hasattr(native_result, "stages"):
        for i, stage_data in enumerate(native_result.stages):
            name = _STAGE_NAMES[i] if i < len(_STAGE_NAMES) else f"Stage {i}"
            metrics = []

            # Extract metrics from stage data
            if hasattr(stage_data, "metrics"):
                for k, v in stage_data.metrics.items():
                    if isinstance(v, (int, float)):
                        metrics.append(QCMetric(k, float(v)))

            stage_status = QCStatus.NA
            if hasattr(stage_data, "status"):
                try:
                    stage_status = QCStatus(stage_data.status)
                except ValueError:
                    pass

            stages.append(QCStageResult(
                stage_name=name,
                stage_index=i,
                score=getattr(stage_data, "score", 0),
                max_score=getattr(stage_data, "max_score", 10),
                status=stage_status,
                metrics=metrics,
                duration_ms=getattr(stage_data, "duration_ms", 0),
            ))

    # Extract key measurements for unified scoring
    if hasattr(native_result, "components"):
        comp = native_result.components
        field_map = {
            "navigation_coverage": "navigation_coverage",
            "snr_db": "snr_db",
            "seafloor_consistency": "seafloor_consistency",
            "penetration_ms": "penetration_ms",
            "spectrum_bandwidth": "spectrum_bandwidth",
            "integrity_dead_pct": "integrity_dead_pct",
        }
        for unified_key, native_key in field_map.items():
            if native_key in comp:
                measurements[unified_key] = comp[native_key]

    # Use native score if available, otherwise compute
    if hasattr(native_result, "total_score"):
        total_score = native_result.total_score
        from ..common.scoring import assign_grade
        grade = assign_grade(total_score)
        status = QCStatus.from_score(total_score)
    else:
        score_result = compute_score(SEISMIC_SCORING_PROFILE, measurements)
        total_score = score_result["total_score"]
        grade = score_result["grade"]
        status = score_result["status"]

    # Collect issues
    issues = []
    for stage in stages:
        issues.extend(stage.issues)
        if stage.status == QCStatus.FAIL:
            issues.append(QCIssue("critical", stage.stage_name.lower(),
                                   f"{stage.stage_name} failed"))

    return QCResult(
        domain=QCDomain.SEISMIC,
        file_name=file_name,
        total_score=total_score,
        grade=grade,
        status=status,
        stages=stages,
        issues=issues,
        duration_ms=duration,
        record_count=getattr(native_result, "trace_count", 0),
    )
