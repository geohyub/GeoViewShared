"""
GeoView QC — Unified Quality Control Framework
================================================
Common QC infrastructure for MAG, Sonar (SSS), and Seismic (SBP/UHR) data.

Provides:
- Unified data models (QCResult, QCScore, QCIssue)
- Scoring engine (linear interpolation, grade boundaries)
- Report generation (Excel, Word, PPT, PDF)
- Web framework base (Flask Blueprint pattern)
- Desktop widget wrappers (CTk)

Architecture:
- Each domain (mag/sonar/seismic/mbes) keeps its analysis logic in-place
- This module provides adapters/wrappers for cross-program integration
- geoview_common/qc/common/ holds shared dataclasses and utilities

Copyright (c) 2025-2026 Geoview Co., Ltd.
"""

__version__ = "0.1.0"
