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
from ..common.scoring import assign_grade, compute_score, MAG_SCORING_PROFILE


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


def _map_status(status: str | None) -> QCStatus:
    normalized = str(status or "N/A").upper()
    if normalized in {"PASS", "GOOD", "EXCELLENT"}:
        return QCStatus.PASS
    if normalized in {"WARN", "ACCEPTABLE"}:
        return QCStatus.WARN
    if normalized in {"FAIL", "POOR"}:
        return QCStatus.FAIL
    return QCStatus.NA


def _empty_timestamp_stats() -> dict[str, Any]:
    return {
        "n": 0,
        "expected_ms": 0,
        "mean_ms": 0,
        "std_ms": 0,
        "min_ms": 0,
        "max_ms": 0,
        "gap_count": 0,
        "reversal_count": 0,
        "duplicate_count": 0,
        "regularity_pct": 0.0,
        "status": "N/A",
    }


def _calc_native_score(analysis: dict, integrity: dict) -> float:
    """Mirror MagQC native score logic so shared results stay interpretable."""
    score = 100.0

    fd_stats = analysis.get("fourth_diff", {}).get("stats", {})
    fd_exceed = float(fd_stats.get("exceedance_pct", 0) or 0)
    if fd_exceed > 0:
        score -= min(30.0, fd_exceed * 3.0)

    noise_status = str(analysis.get("noise", {}).get("status", "N/A")).upper()
    if noise_status == "FAIL":
        score -= 30.0
    elif noise_status == "WARN":
        score -= 15.0

    spike_pct = float(analysis.get("spikes", {}).get("spike_pct", 0) or 0)
    if spike_pct > 2.0:
        score -= 20.0
    elif spike_pct > 0.5:
        score -= 10.0
    elif spike_pct > 0:
        score -= 5.0

    valid_pct = float(integrity.get("validPct", 100) or 100)
    if valid_pct < 95.0:
        score -= 20.0
    elif valid_pct < 99.0:
        score -= 10.0

    return round(max(0.0, min(100.0, score)), 1)


def _build_integrity_summary(
    check_integrity_fn,
    data_records: list[dict],
    parsed_result: Optional[dict],
    timestamp_stats: dict[str, Any],
) -> dict[str, Any]:
    """Use native parser integrity when available, otherwise synthesize a safe summary."""
    if isinstance(parsed_result, dict) and parsed_result.get("integrity") is not None:
        return check_integrity_fn(parsed_result)

    total = len(data_records)
    valid = sum(1 for row in data_records if row.get("field") is not None)
    corrupt = max(0, total - valid)
    valid_pct = round((valid / total) * 100.0, 2) if total > 0 else 0.0

    time_reversals = int(timestamp_stats.get("reversal_count", 0) or 0)
    time_gaps = int(timestamp_stats.get("gap_count", 0) or 0)
    time_duplicates = int(timestamp_stats.get("duplicate_count", 0) or 0)
    time_issues = time_reversals + time_gaps + time_duplicates

    if total <= 0:
        status = "N/A"
    elif valid_pct >= 99.0 and time_issues == 0:
        status = "EXCELLENT"
    elif valid_pct >= 95.0:
        status = "GOOD"
    elif valid_pct >= 80.0:
        status = "ACCEPTABLE"
    else:
        status = "POOR"

    return {
        "totalLines": total,
        "validRecords": valid,
        "corruptCount": corrupt,
        "recoveredCount": 0,
        "timeReversals": time_reversals,
        "timeGaps": time_gaps,
        "timeDuplicates": time_duplicates,
        "validPct": valid_pct,
        "status": status,
    }


def _build_issues(analysis: dict, integrity: dict, timestamp_stats: dict[str, Any]) -> list[QCIssue]:
    issues: list[QCIssue] = []

    noise = analysis.get("noise", {})
    noise_pp = float(noise.get("pp", 0) or 0)
    if str(noise.get("status", "")).upper() == "FAIL":
        issues.append(QCIssue("critical", "noise", f"Noise P-P={noise_pp:.3f} nT exceeds limit", "full line"))
    elif str(noise.get("status", "")).upper() == "WARN":
        issues.append(QCIssue("warning", "noise", f"Noise P-P={noise_pp:.3f} nT is in warning range", "full line"))

    fd_stats = analysis.get("fourth_diff", {}).get("stats", {})
    fd_exceed = float(fd_stats.get("exceedance_pct", 0) or 0)
    if fd_exceed > 0:
        severity = "critical" if fd_exceed > 5.0 else "warning"
        issues.append(
            QCIssue(
                severity,
                "fourth_diff",
                f"4th difference exceedance={fd_exceed:.1f}%, max={float(fd_stats.get('max_abs', 0) or 0):.3f} nT",
                "threshold exceedance",
            )
        )

    spikes = analysis.get("spikes", {})
    spike_pct = float(spikes.get("spike_pct", 0) or 0)
    spike_count = int(spikes.get("spike_count", 0) or 0)
    spike_positions = [f"#{item.get('index')}" for item in spikes.get("spikes", [])[:5]]
    spike_location = ", ".join(spike_positions) if spike_positions else "spike region"
    if spike_count > 0:
        issues.append(
            QCIssue(
                "critical" if spike_pct > 2.0 else "warning",
                "spike",
                f"Spike count={spike_count}, rate={spike_pct:.2f}%",
                spike_location,
            )
        )

    corrupt = int(integrity.get("corruptCount", 0) or 0)
    if corrupt > 0:
        issues.append(
            QCIssue(
                "warning",
                "integrity",
                f"Corrupt records detected={corrupt}",
                f"valid {float(integrity.get('validPct', 0) or 0):.1f}%",
            )
        )

    if (
        int(timestamp_stats.get("gap_count", 0) or 0)
        or int(timestamp_stats.get("reversal_count", 0) or 0)
        or int(timestamp_stats.get("duplicate_count", 0) or 0)
    ):
        issues.append(
            QCIssue(
                "critical" if int(timestamp_stats.get("reversal_count", 0) or 0) else "warning",
                "timing",
                (
                    f"Timing continuity issue: gap={int(timestamp_stats.get('gap_count', 0) or 0)}, "
                    f"reversal={int(timestamp_stats.get('reversal_count', 0) or 0)}, "
                    f"duplicate={int(timestamp_stats.get('duplicate_count', 0) or 0)}"
                ),
                "time sequence",
            )
        )

    return issues


def analyze_mag_data(
    data_records: list[dict],
    file_name: str = "",
    line_name: str = "",
    fd_threshold: float = 0.5,
    pp_limit: float = 1.0,
    mad_mult: float = 5.0,
    spike_window: int = 11,
    parsed_result: Optional[dict] = None,
    detrend: bool = True,
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
        QCResult with stages for noise, 4th_diff, spikes, integrity, timing.
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

    if not data_records:
        return QCResult(
            domain=QCDomain.MAG,
            file_name=file_name,
            line_name=line_name,
            total_score=0.0,
            grade=QCGrade.F,
            status=QCStatus.NA,
            issues=[QCIssue("info", "empty", "No MAG records were provided")],
            duration_ms=(time.perf_counter() - t0) * 1000,
            record_count=0,
        )

    # Run native MagQC analysis
    result = run_full_analysis(
        data_records,
        fd_threshold=fd_threshold,
        pp_limit=pp_limit,
        mad_mult=mad_mult,
        spike_window=spike_window,
        detrend=detrend,
    )
    if "epochMs" in data_records[0] or "timeMs" in data_records[0]:
        timestamp_stats = analyze_timestamp_continuity(data_records).get("stats", {})
    else:
        timestamp_stats = _empty_timestamp_stats()
    integrity = _build_integrity_summary(check_integrity, data_records, parsed_result, timestamp_stats)

    duration = (time.perf_counter() - t0) * 1000

    # Build stages
    stages = []

    # Stage 1: Noise
    noise = result.get("noise", {})
    noise_pp = float(noise.get("pp", 0) or 0)
    noise_status = _map_status(noise.get("status"))
    noise_score = 30.0 if noise_status == QCStatus.PASS else (15.0 if noise_status == QCStatus.WARN else 0.0)
    stages.append(QCStageResult(
        stage_name="Noise Analysis",
        stage_index=0,
        score=noise_score,
        max_score=30,
        status=noise_status,
        metrics=[
            QCMetric("Peak-to-Peak", noise_pp, "nT", noise_status),
            QCMetric("Std Dev", float(noise.get("std", 0) or 0), "nT"),
            QCMetric("RMS", float(noise.get("rms", 0) or 0), "nT"),
        ],
    ))

    # Stage 2: 4th Difference
    fd = result.get("fourth_diff", {})
    fd_stats = fd.get("stats", {})
    fd_exceed = float(fd_stats.get("exceedance_pct", 0) or 0)
    fd_status = QCStatus.PASS if fd_exceed <= 1 else (QCStatus.WARN if fd_exceed <= 5 else QCStatus.FAIL)
    fd_score = max(0.0, 30.0 - min(30.0, fd_exceed * 3.0))
    stages.append(QCStageResult(
        stage_name="4th Difference",
        stage_index=1,
        score=fd_score,
        max_score=30,
        status=fd_status,
        metrics=[
            QCMetric("Exceedance", fd_exceed, "%", fd_status),
            QCMetric("RMS", float(fd_stats.get("rms", 0) or 0), "nT"),
            QCMetric("Max Abs", float(fd_stats.get("max_abs", 0) or 0), "nT"),
        ],
    ))

    # Stage 3: Spikes
    spikes = result.get("spikes", {})
    spike_pct = float(spikes.get("spike_pct", 0) or 0)
    spike_status = QCStatus.PASS if spike_pct <= 0 else (QCStatus.WARN if spike_pct <= 2 else QCStatus.FAIL)
    if spike_pct > 2.0:
        spike_score = 0.0
    elif spike_pct > 0.5:
        spike_score = 10.0
    elif spike_pct > 0:
        spike_score = 15.0
    else:
        spike_score = 20.0
    stages.append(QCStageResult(
        stage_name="Spike Detection",
        stage_index=2,
        score=spike_score,
        max_score=20,
        status=spike_status,
        metrics=[
            QCMetric("Spike Rate", spike_pct, "%", spike_status),
            QCMetric("Spike Count", float(spikes.get("spike_count", 0) or 0), ""),
            QCMetric("MAD", float(spikes.get("mad", 0) or 0), "nT"),
        ],
    ))

    # Stage 4: Integrity
    int_pct = float(integrity.get("validPct", 100) or 100)
    int_status = _map_status(integrity.get("status"))
    int_score = 20.0 if int_pct >= 99 else (10.0 if int_pct >= 95 else 0.0)
    stages.append(QCStageResult(
        stage_name="Data Integrity",
        stage_index=3,
        score=int_score,
        max_score=20,
        status=int_status,
        metrics=[
            QCMetric("Valid Records", int_pct, "%", int_status),
            QCMetric("Corrupt Count", float(integrity.get("corruptCount", 0) or 0), ""),
            QCMetric("Recovered Count", float(integrity.get("recoveredCount", 0) or 0), ""),
        ],
    ))

    # Stage 5: Timestamp continuity (informational, not part of native score)
    ts_status = _map_status(timestamp_stats.get("status"))
    stages.append(QCStageResult(
        stage_name="Timestamp Continuity",
        stage_index=4,
        score=0.0,
        max_score=0.0,
        status=ts_status,
        metrics=[
            QCMetric("Regularity", float(timestamp_stats.get("regularity_pct", 0) or 0), "%", ts_status),
            QCMetric("Gap Count", float(timestamp_stats.get("gap_count", 0) or 0), ""),
            QCMetric("Reversal Count", float(timestamp_stats.get("reversal_count", 0) or 0), ""),
            QCMetric("Duplicate Count", float(timestamp_stats.get("duplicate_count", 0) or 0), ""),
        ],
        detail={"informational": True},
    ))

    # Compute measurement snapshot for downstream consumers
    measurements = {
        "noise_pp": noise_pp,
        "fourth_diff_exceedance": fd_exceed,
        "spike_pct": spike_pct,
        "integrity_pct": int_pct,
        "timestamp_regularity": float(timestamp_stats.get("regularity_pct", 0) or 0),
    }
    shared_score_result = compute_score(MAG_SCORING_PROFILE, measurements)
    total_score = _calc_native_score(result, integrity)
    grade = assign_grade(total_score)
    status = QCStatus.from_score(total_score)
    issues = _build_issues(result, integrity, timestamp_stats)

    return QCResult(
        domain=QCDomain.MAG,
        file_name=file_name,
        line_name=line_name,
        total_score=total_score,
        grade=grade,
        status=status,
        stages=stages,
        issues=issues,
        duration_ms=duration,
        record_count=len(data_records),
        extra={
            "native_summary": result.get("summary", {}),
            "measurements": measurements,
            "integrity": integrity,
            "timestamp": timestamp_stats,
            "shared_score_result": shared_score_result,
        },
    )


def analyze_mag_file(
    file_path: str | Path,
    line_name: str = "",
    fd_threshold: float = 0.5,
    pp_limit: float = 1.0,
    mad_mult: float = 5.0,
    spike_window: int = 11,
    detrend: bool = True,
) -> QCResult:
    """Read a MAG file, parse it with native MagQC logic, and return QCResult."""
    _ensure_magqc_importable()

    try:
        import parsers
    except ImportError:
        return QCResult(
            domain=QCDomain.MAG,
            file_name=str(file_path),
            line_name=line_name,
            status=QCStatus.NA,
            issues=[QCIssue("critical", "import", "MagQC parser module not found")],
        )

    path = Path(file_path)
    if not path.exists():
        return QCResult(
            domain=QCDomain.MAG,
            file_name=path.name,
            line_name=line_name,
            status=QCStatus.NA,
            issues=[QCIssue("critical", "file", f"File not found: {path}")],
        )

    try:
        text = path.read_text(encoding="utf-8", errors="replace")
        fmt = parsers.detect_format(text)
        if fmt in ("g882-jako", "g882-vena"):
            parsed = parsers.parse_g882(path.name, text)
        elif fmt == "explorer":
            parsed = parsers.parse_explorer(text)
        else:
            return QCResult(
                domain=QCDomain.MAG,
                file_name=path.name,
                line_name=line_name,
                status=QCStatus.NA,
                issues=[QCIssue("warning", "format", f"Unsupported MAG format: {fmt}")],
            )
    except Exception as exc:
        return QCResult(
            domain=QCDomain.MAG,
            file_name=path.name,
            line_name=line_name,
            status=QCStatus.NA,
            issues=[QCIssue("critical", "parse", f"Failed to parse MAG file: {exc}")],
        )

    return analyze_mag_data(
        parsed.get("data", []),
        file_name=path.name,
        line_name=line_name or path.stem,
        fd_threshold=fd_threshold,
        pp_limit=pp_limit,
        mad_mult=mad_mult,
        spike_window=spike_window,
        parsed_result=parsed,
        detrend=detrend,
    )


__all__ = ["analyze_mag_data", "analyze_mag_file"]
