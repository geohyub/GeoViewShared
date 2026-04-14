"""
geoview_cpt.parsers
================================
CPT domain parsers (Phase A-2).

Each parser follows the :class:`geoview_pyside6.parsers.BaseParser` protocol
from Phase A-1 so they can register with the parser harness and be routed
by format detection.

Currently implemented:
    cpet_it_v30.read_cpt_v30    CPeT-IT v.3.9.1.3 .cpt reader (A2.0)
"""
from __future__ import annotations

from geoview_cpt.parsers.cpet_it_v30 import (
    CPetItReadError,
    read_cpt_v30,
    read_cpt_v30_bytes,
)

__all__ = [
    "read_cpt_v30",
    "read_cpt_v30_bytes",
    "CPetItReadError",
]
