"""
geoview_pyside6.parsers.samples
================================
Reference parser implementations used by the test suite and as templates
for domain-specific parsers (CPT, Mag, AGS4, ...).

Currently ships:
    CSVFallbackParser, CSVPayload  — generic CSV fallback (Phase A-2 A2.4 seed)
"""
from __future__ import annotations

from geoview_pyside6.parsers.samples.csv_fallback import (
    CSVFallbackParser,
    CSVPayload,
)

__all__ = ["CSVFallbackParser", "CSVPayload"]
