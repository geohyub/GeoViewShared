"""
geoview_pyside6.parsers
================================
Parser harness for GeoView software (Phase A-1 A1.1).

모든 도메인 파서 (CPT, Mag, SegY, AGS4, ...) 가 따르는 공통 인터페이스와
탐지/파싱 라우팅 Registry.

Public API:
    BaseParser          Structural Protocol interface
    DetectedFormat      Detection result (frozen dataclass)
    ParserResult        Parse output dataclass
    ParserError         Error base class
    DetectError, ParseError
    ParserRegistry      Instance-based registry (테스트 격리용)
    RegistryError
    default_registry    Module-level default
    register_parser     Decorator for default-registry registration
    detect, parse       Convenience functions
    chunk_reader, first_n_lines, sniff_encoding    IO helpers

Reference implementation:
    geoview_pyside6.parsers.samples.csv_fallback.CSVFallbackParser

Consumers (Phase A-2+):
    geoview_cpt.parsers.cpet_it_v30
    geoview_cpt.parsers.excel_yw / excel_jako / field_book / cpt_text_bundle
    geoview_cpt.ags_convert.reader (AGS4)
"""
from __future__ import annotations

from geoview_pyside6.parsers.base import (
    BaseParser,
    DetectedFormat,
    DetectError,
    ParseError,
    ParserError,
    ParserResult,
)
from geoview_pyside6.parsers.registry import (
    ParserRegistry,
    RegistryError,
    default_registry,
    detect,
    parse,
    register_parser,
)
from geoview_pyside6.parsers.utils import (
    FIRST_N_LINES_DEFAULT,
    chunk_reader,
    first_n_lines,
    sniff_encoding,
)

__all__ = [
    # base
    "BaseParser",
    "DetectedFormat",
    "ParserResult",
    "ParserError",
    "DetectError",
    "ParseError",
    # registry
    "ParserRegistry",
    "RegistryError",
    "default_registry",
    "register_parser",
    "detect",
    "parse",
    # utils
    "chunk_reader",
    "first_n_lines",
    "sniff_encoding",
    "FIRST_N_LINES_DEFAULT",
]
