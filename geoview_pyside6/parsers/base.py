"""
geoview_pyside6.parsers.base
================================
BaseParser Protocol and supporting dataclasses for the GeoView parser harness.

Design decisions:
 - **Protocol over ABC**: duck typing 유지하면서 `runtime_checkable` 로 isinstance 체크 지원.
   기존 도메인 코드를 ABC 상속으로 강제하지 않음 (MagQC 교훈 #16 — parsers 실제 API 확인).
 - **Frozen DetectedFormat**: 탐지 결과는 불변. Registry 가 정렬/비교하는 동안 안전.
 - **Mutable ParserResult**: parse 중 warnings/errors 가 누적되므로 변경 가능.
 - **Error hierarchy**: ParserError 단일 루트 + DetectError/ParseError 세분화.
   RegistryError 는 registry 모듈에서 ParserError 를 상속.

Phase A-1 A1.1 산출물.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

__all__ = [
    "DetectedFormat",
    "ParserResult",
    "BaseParser",
    "ParserError",
    "DetectError",
    "ParseError",
]


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class ParserError(Exception):
    """
    Base exception for the parser harness.

    Optional `path` attribute captures the file that triggered the error,
    useful for UI surfacing via CPTPrep 임포트 마법사 (B1.2).
    """

    def __init__(self, message: str, *, path: Path | None = None) -> None:
        super().__init__(message)
        self.path: Path | None = path

    def __str__(self) -> str:
        base = super().__str__()
        if self.path is not None:
            return f"{base} (path={self.path})"
        return base


class DetectError(ParserError):
    """Raised when format detection itself fails unexpectedly (not just 'no match')."""


class ParseError(ParserError):
    """Raised when parse fails after successful (or forced) detection."""


# ---------------------------------------------------------------------------
# Detection result + parse result
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DetectedFormat:
    """
    Result of `BaseParser.detect()` — recognition confidence + format metadata.

    Attributes:
        code:        machine-readable parser code, e.g. "ags4", "cpet_it_v30"
        confidence:  [0.0, 1.0], 1.0 = certain
        version:     optional format version string, e.g. "4.1", "v30"
        notes:       human-readable remarks (delimiter, encoding hint, ...)
    """

    code: str
    confidence: float
    version: str = ""
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.code:
            raise ValueError("DetectedFormat.code must not be empty")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(
                f"DetectedFormat.confidence must be in [0.0, 1.0], got {self.confidence}"
            )


@dataclass
class ParserResult:
    """
    Complete parser output — domain payload + diagnostic streams + provenance.

    Attributes:
        payload:      domain model (e.g. CPTSounding, MagLine, list[dict], ...)
        source_path:  original file path
        detected:     DetectedFormat that led to this parse
        warnings:     non-fatal issues (truncated rows, encoding fallback, ...)
        errors:       fatal-but-recovered issues (empty → result.ok == True)
        metadata:     free-form dict for row counts, timings, bytes read, ...
    """

    payload: Any
    source_path: Path
    detected: DetectedFormat
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        """True when no fatal errors were recorded."""
        return not self.errors


# ---------------------------------------------------------------------------
# Parser Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class BaseParser(Protocol):
    """
    Structural protocol for all GeoView parsers.

    MagQC 교훈 #16 (parsers 실제 API 확인) 을 코드 레벨에서 강제하기 위해
    Protocol + runtime_checkable 사용. 구현자는 상속 없이도 isinstance 체크를 통과.

    Required class attributes:
        CODE:          unique machine-readable code (e.g. "cpet_it_v30")
        DISPLAY_NAME:  user-facing name (MagQC 교훈 #17 — CODE vs 표시명 분리)

    Required methods:
        detect(path) -> DetectedFormat | None
            None 반환 = "이 파서는 이 파일을 처리 못함" (정상 non-match).
            예외 발생 = 탐지 자체의 버그 (Registry 가 swallow).

        parse(path)  -> ParserResult
            성공 시 ParserResult 반환 (warnings/errors 내부 누적 허용).
            치명 실패 시 ParseError 발생.

    Example::

        class MyFormatParser:
            CODE = "my_fmt"
            DISPLAY_NAME = "My Format (v1)"

            def detect(self, path: Path) -> DetectedFormat | None:
                if path.suffix != ".my":
                    return None
                return DetectedFormat(code=self.CODE, confidence=0.95, version="1")

            def parse(self, path: Path) -> ParserResult:
                ...
    """

    CODE: str
    DISPLAY_NAME: str

    def detect(self, path: Path) -> DetectedFormat | None: ...

    def parse(self, path: Path) -> ParserResult: ...
