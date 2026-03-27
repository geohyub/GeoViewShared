"""
QC MAG Domain Adapter
=====================
Wraps MagQC analysis functions (core.py, parsers.py) to produce
unified QCResult objects. Does NOT duplicate analysis logic —
imports from the original MagQC module.

Usage:
    from geoview_common.qc.mag import analyze_mag_file

Copyright (c) 2025-2026 Geoview Co., Ltd.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Optional

from ..common.models import (
    QCDomain, QCStatus, QCGrade, QCMetric, QCIssue,
    QCStageResult, QCResult,
)
from ..common.scoring import compute_score, MAG_SCORING_PROFILE


def _ensure_magqc_importable():
    """Add MagQC to sys.path if not already importable."""
    magqc_paths = [
        Path(r"E:\Software\QC\MagQC"),
        Path(__file__).resolve().parents[4] / "QC" / "MagQC",
    ]
    for p in magqc_paths:
        if p.exists() and str(p) not in sys.path:
            sys.path.insert(0, str(p))
            return True
    return False


def analyze_mag_data(
    data_records: list[dict],
    file_name: str = "",
    line_name: str = "",
    fd_threshold: float = 0.5,
    pp_limit: float = 1.0,
    mad_mult: float = 5.0,
    spike_window: int = 11,
) -> QCResult:
    """Run MAG QC analysis and return unified QCResult.

    Args:
        data_records: Parsed MAG records (must have 'field' key).
        file_name: Source file name.
        line_name: Survey line identifier.
        fd_threshold: 4th difference threshold (nT).
        pp_limit: Noise peak-to-peak limit (nT).
        mad_mult: MAD multiplier for spike detection.
        spike_window: Moving median window size.

    Returns:
        QCResult with stages for noise, 4th_diff, spikes, integrity.
    """
    _ensure_magqc_importable()

    try:
        from core import (
            run_full_analysis, check_integrity,
            analyze_timestamp_continuity,
        )
    except ImportError:
        return QCResult(
            domain=QCDomain.MAG,
            file_name=file_name,
            line_name=line_name,
            status=QCStatus.NA,
            issues=[QCIssue("critical", "import", "MagQC core module not found")],
        )

    import time
    t0 = time.perf_counter()

    # Run native MagQC analysis
    result = run_full_analysis(
        data_records,
        fd_threshold=fd_threshold,
        pp_limit=pp_limit,
        mad_mult=mad_mult,
        spike_window=spike_window,
    )
    integrity = check_integrity({"data": data_records})

    duration = (time.perf_counter() - t0) * 1000

    # Build stages
    stages = []

    # Stage 1: Noise
    noise = result.get("noise", {})
    noise_pp = noise.get("peak_to_peak", 0)
    stages.append(QCStageResult(
        stage_name="Noise Analysis",
        stage_index=0,
        score=25 if noise.get("status") == "PASS" else (15 if noise.get("status") == "WARN" else 5),
        max_score=25,
        status=QCStatus(noise.get("status", "N/A")),
        metrics=[
            QCMetric("Peak-to-Peak", noise_pp, "nT", QCStatus(noise.get("status", "N/A"))),
            QCMetric("Std Dev", noise.get("std_dev", 0), "nT"),
        ],
    ))

    # Stage 2: 4th Difference
    fd = result.get("fourth_diff", {})
    fd_stats = fd.get("stats", {})
    fd_exceed = fd_stats.get("exceedance_pct", 0)
    fd_status = QCStatus.PASS if fd_exceed < 1 else (QCStatus.WARN if fd_exceed < 5 else QCStatus.FAIL)
    stages.append(QCStageResult(
        stage_name="4th Difference",
        stage_index=1,
        score=25 * max(0, 1 - fd_exceed / 10),
        max_score=25,
        status=fd_status,
        metrics=[
            QCMetric("Exceedance", fd_exceed, "%", fd_status),
            QCMetric("RMS", fd_stats.get("rms", 0), "nT"),
            QCMetric("Max Abs", fd_stats.get("max_abs", 0), "nT"),
        ],
    ))

    # Stage 3: Spikes
    spikes = result.get("spikes", {})
    spike_pct = spikes.get("spike_pct", 0)
    spike_status = QCStatus.PASS if spike_pct < 0.5 else (QCStatus.WARN if spike_pct < 2 else QCStatus.FAIL)
    stages.append(QCStageResult(
        stage_name="Spike Detection",
        stage_index=2,
        score=20 * max(0, 1 - spike_pct / 5),
        max_score=20,
        status=spike_status,
        metrics=[
            QCMetric("Spike Rate", spike_pct, "%", spike_status),
            QCMetric("Spike Count", spikes.get("spike_count", 0), ""),
            QCMetric("MAD", spikes.get("mad", 0), "nT"),
        ],
    ))

    # Stage 4: Integrity
    int_pct = integrity.get("validPct", 100)
    int_status = QCStatus.PASS if int_pct >= 99 else (QCStatus.WARN if int_pct >= 95 else QCStatus.FAIL)
    stages.append(QCStageResult(
        stage_name="Data Integrity",
        stage_index=3,
        score=15 * min(1, int_pct / 100),
        max_score=15,
        status=int_status,
        metrics=[
            QCMetric("Valid Records", int_pct, "%", int_status),
            QCMetric("Corrupt Count", integrity.get("corruptCount", 0), ""),
        ],
    ))

    # Compute unified score
    measurements = {
        "noise_pp": noise_pp,
        "fourth_diff_exceedance": fd_exceed,
        "spike_pct": spike_pct,
        "integrity_pct": int_pct,
        "timestamp_regularity": 95.0,  # placeholder if not computed
    }
    score_result = compute_score(MAG_SCORING_PROFILE, measurements)

    # Build issues
    issues = []
    if noise.get("status") == "FAIL":
        issues.append(QCIssue("critical", "noise", f"Noise PP={noise_pp:.2f} nT exceeds limit"))
    if fd_exceed > 5:
        issues.append(QCIssue("critical", "fourth_diff", f"4th diff exceedance={fd_exceed:.1f}%"))
    if spike_pct > 2:
        issues.append(QCIssue("warning", "spike", f"Spike rate={spike_pct:.1f}%"))

    return QCResult(
        domain=QCDomain.MAG,
        file_name=file_name,
        line_name=line_name,
        total_score=score_result["total_score"],
        grade=score_result["grade"],
        status=score_result["status"],
        stages=stages,
        issues=issues,
        duration_ms=duration,
        record_count=len(data_records),
    )
