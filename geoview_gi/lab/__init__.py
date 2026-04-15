"""
geoview_gi.lab
================================
External laboratory report parsers (Phase A-2 A2.18).

Currently implemented:

    sa_geolab   SA Geolab Pte Ltd PDF summary reader (JAKO Korea
                vendor reports, 158 p / 56 p)
"""
from __future__ import annotations

from geoview_gi.lab.sa_geolab import (
    FAILURE_CODES,
    STATE_CODES,
    TEST_TYPES,
    SAGeolabParseError,
    parse_sa_geolab_pdf,
)

__all__ = [
    "parse_sa_geolab_pdf",
    "SAGeolabParseError",
    "TEST_TYPES",
    "FAILURE_CODES",
    "STATE_CODES",
]
