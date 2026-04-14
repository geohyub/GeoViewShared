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
from geoview_cpt.parsers.excel_jako import (
    JakoParseError,
    JakoParseOptions,
    detect_jako_xls,
    parse_jako_xls,
)
from geoview_cpt.parsers.excel_yw import (
    YwParseError,
    YwParseOptions,
    detect_yw_xlsx,
    parse_yw_xlsx,
)
from geoview_cpt.parsers.field_book import (
    FieldBookEntry,
    FieldBookParseError,
    FieldBookTable,
    detect_field_book,
    parse_field_book,
)

__all__ = [
    # CPeT-IT v30
    "read_cpt_v30",
    "read_cpt_v30_bytes",
    "CPetItReadError",
    # YW Excel (HELMS Yawol)
    "parse_yw_xlsx",
    "detect_yw_xlsx",
    "YwParseOptions",
    "YwParseError",
    # JAKO Excel (Gouda WISON)
    "parse_jako_xls",
    "detect_jako_xls",
    "JakoParseOptions",
    "JakoParseError",
    # Field book (야장)
    "parse_field_book",
    "detect_field_book",
    "FieldBookEntry",
    "FieldBookTable",
    "FieldBookParseError",
]
