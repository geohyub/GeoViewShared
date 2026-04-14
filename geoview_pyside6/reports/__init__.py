"""
geoview_pyside6.reports
================================
Shared report builder facade (Phase A-1 A1.6).

Wraps the existing cross-domain generators in
``geoview_common.qc.common.report_builder`` with:

 1. **Atomic writes** via :func:`geoview_pyside6.io_safe.atomic_writer`,
    so a crash mid-render leaves no torn Excel/Word/PDF next to good
    files.
 2. **A single facade** (``ReportBuilder``) that emits all three formats
    in one call, returning a :class:`ReportManifest` with absolute paths
    and file sizes for Deliverables Pack manifests.
 3. **No style drift**: the facade delegates to the mature generators
    unchanged, so existing MagQC/SonarQC reports diff ≤1% (acceptance
    criterion from master plan §5.1 A1.6).

Public API:
    ReportBuilder, ReportManifest, ReportFormat, ReportBuildError
"""
from __future__ import annotations

from geoview_pyside6.reports.builder import (
    ReportBuilder,
    ReportBuildError,
    ReportFormat,
    ReportManifest,
)

__all__ = [
    "ReportBuilder",
    "ReportManifest",
    "ReportFormat",
    "ReportBuildError",
]
