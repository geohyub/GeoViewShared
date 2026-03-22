"""
QC Common Data Models
=====================
Unified dataclass definitions shared across MAG, Sonar, and Seismic QC.

These models provide a consistent interface for:
- Individual metrics (QCMetric)
- Analysis stage results (QCStageResult)
- Overall file/line QC results (QCResult)
- Issue tracking (QCIssue)
- Project-level summaries (QCProjectSummary)

Each domain (mag/sonar/seismic) maps its native results to these models
via adapter functions, keeping domain logic in-place.

Copyright (c) 2025-2026 Geoview Co., Ltd.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class QCDomain(str, Enum):
    """Data domain identifier."""
    MAG = "mag"
    SONAR = "sonar"
    SEISMIC = "seismic"
    MBES = "mbes"


class QCStatus(str, Enum):
    """QC pass/fail status."""
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"
    NA = "N/A"

    @classmethod
    def from_score(cls, score: float) -> QCStatus:
        if score >= 80:
            return cls.PASS
        elif score >= 50:
            return cls.WARN
        return cls.FAIL


class QCGrade(str, Enum):
    """Letter grade (A-F)."""
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    F = "F"


# ---------------------------------------------------------------------------
# Core Data Models
# ---------------------------------------------------------------------------

@dataclass
class QCMetric:
    """Single QC measurement with value, unit, and status.

    Examples:
        QCMetric("Peak-to-Peak Noise", 0.8, "nT", QCStatus.PASS)
        QCMetric("SNR", 18.5, "dB", QCStatus.PASS)
        QCMetric("Altitude Compliance", 92.3, "%", QCStatus.PASS)
    """
    name: str
    value: float
    unit: str = ""
    status: QCStatus = QCStatus.NA
    detail: str = ""

    @property
    def display(self) -> str:
        """Human-readable value with unit."""
        if self.unit == "%":
            return f"{self.value:.1f}%"
        elif self.unit == "dB":
            return f"{self.value:.1f} dB"
        elif self.unit:
            return f"{self.value:.2f} {self.unit}"
        return f"{self.value:.2f}"


@dataclass
class QCIssue:
    """Quality issue detected during analysis.

    Attributes:
        severity: "critical", "warning", "info"
        category: Domain-specific category (e.g., "noise", "spike", "gap")
        description: Human-readable issue description
        location: Where the issue was found (line name, trace index, etc.)
    """
    severity: str  # "critical" | "warning" | "info"
    category: str
    description: str
    location: str = ""
    suggestion: str = ""


@dataclass
class QCStageResult:
    """Result from a single QC analysis stage.

    Used for pipeline-style analysis (e.g., SeismicQC's 10-stage pipeline,
    SonarQC's multi-aspect analysis, MagQC's sequential checks).
    """
    stage_name: str
    stage_index: int = 0
    score: float = 0.0
    max_score: float = 10.0
    status: QCStatus = QCStatus.NA
    metrics: list[QCMetric] = field(default_factory=list)
    issues: list[QCIssue] = field(default_factory=list)
    detail: dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0

    @property
    def normalized_score(self) -> float:
        """Score as 0-100 percentage of max."""
        if self.max_score <= 0:
            return 0.0
        return min(100.0, (self.score / self.max_score) * 100.0)


@dataclass
class QCResult:
    """Complete QC result for a single file or survey line.

    This is the primary output of any QC analysis, regardless of domain.
    Each domain adapter maps native results to this structure.
    """
    # Identity
    domain: QCDomain
    file_name: str
    line_name: str = ""
    analysis_type: str = "full"  # "full", "processed", "raw"

    # Scoring
    total_score: float = 0.0
    grade: QCGrade = QCGrade.F
    status: QCStatus = QCStatus.NA

    # Pipeline stages
    stages: list[QCStageResult] = field(default_factory=list)

    # Aggregated issues
    issues: list[QCIssue] = field(default_factory=list)

    # Metadata
    timestamp: datetime = field(default_factory=datetime.now)
    duration_ms: float = 0.0
    record_count: int = 0
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def issue_counts(self) -> dict[str, int]:
        """Count issues by severity."""
        counts = {"critical": 0, "warning": 0, "info": 0}
        for issue in self.issues:
            if issue.severity in counts:
                counts[issue.severity] += 1
        return counts

    @property
    def all_metrics(self) -> list[QCMetric]:
        """Flatten all metrics from all stages."""
        result = []
        for stage in self.stages:
            result.extend(stage.metrics)
        return result


@dataclass
class QCProjectSummary:
    """Aggregated QC summary for an entire project (multiple files/lines).

    Used for dashboard KPI cards and project-level reporting.
    """
    project_name: str
    client: str = ""
    vessel: str = ""
    domain: Optional[QCDomain] = None  # None = multi-domain

    # Counts
    total_files: int = 0
    analyzed_files: int = 0
    total_lines: int = 0

    # Scores
    avg_score: float = 0.0
    min_score: float = 0.0
    max_score: float = 0.0

    # Status distribution
    pass_count: int = 0
    warn_count: int = 0
    fail_count: int = 0

    # Issues
    total_issues: int = 0
    critical_issues: int = 0

    # Per-domain results (for multi-domain projects)
    results: list[QCResult] = field(default_factory=list)

    @property
    def overall_status(self) -> QCStatus:
        if self.fail_count > 0:
            return QCStatus.FAIL
        elif self.warn_count > 0:
            return QCStatus.WARN
        elif self.pass_count > 0:
            return QCStatus.PASS
        return QCStatus.NA

    @property
    def completion_pct(self) -> float:
        if self.total_files <= 0:
            return 0.0
        return (self.analyzed_files / self.total_files) * 100.0
