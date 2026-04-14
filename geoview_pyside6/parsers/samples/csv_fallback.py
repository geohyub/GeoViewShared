"""
geoview_pyside6.parsers.samples.csv_fallback
================================
Reference CSV parser — demonstrates BaseParser protocol conformance and
serves as the seed for the Phase A-2 A2.4 generic CSV fallback (CPTPrep).

Detection strategy:
    1. File extension ∈ {.csv, .txt, .tsv}
    2. first_n_lines(n=200) 에서 comma/tab/semicolon 중 하나가 stable
       (같은 count 가 ≥ 80% 의 non-empty 줄에 등장)
    3. Confidence = 0.6 + stability * 0.3 (최대 0.95, fallback 특성상 상한)

Parse strategy:
    - Winning delimiter 로 모든 줄 split
    - 첫 줄 = header, 나머지 = rows
    - column count 불일치는 warnings 에만 기록 (fatal 아님)
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from geoview_pyside6.parsers.base import (
    DetectedFormat,
    ParseError,
    ParserResult,
)
from geoview_pyside6.parsers.utils import first_n_lines, sniff_encoding

__all__ = ["CSVFallbackParser", "CSVPayload"]


@dataclass
class CSVPayload:
    """Simple CSV payload — header + rows as list[list[str]]."""

    header: list[str]
    rows: list[list[str]]
    encoding: str
    delimiter: str


class CSVFallbackParser:
    """
    Generic CSV fallback parser (BaseParser protocol-compliant, no ABC).

    This is the reference implementation that the ParserRegistry test suite
    uses to validate the full detect → parse round-trip.
    """

    CODE: str = "csv_fallback"
    DISPLAY_NAME: str = "Generic CSV"

    _EXTS: tuple[str, ...] = (".csv", ".txt", ".tsv")
    _DELIMS: tuple[str, ...] = (",", "\t", ";")
    _MIN_STABILITY: float = 0.80
    _MIN_LINES: int = 2  # header + at least one data row

    # ------------------------------------------------------------------ detect

    def detect(self, path: Path) -> DetectedFormat | None:
        path = Path(path)
        if path.suffix.lower() not in self._EXTS:
            return None

        try:
            lines = first_n_lines(path, n=200)
        except (OSError, ValueError):
            return None

        non_empty = [ln for ln in lines if ln.strip()]
        if len(non_empty) < self._MIN_LINES:
            return None

        best_delim: str | None = None
        best_ratio: float = 0.0
        for delim in self._DELIMS:
            counts = [ln.count(delim) for ln in non_empty]
            if not counts:
                continue
            mode = max(set(counts), key=counts.count)
            if mode == 0:
                continue
            stable = sum(1 for c in counts if c == mode)
            ratio = stable / len(counts)
            if ratio > best_ratio:
                best_ratio = ratio
                best_delim = delim

        if best_delim is None or best_ratio < self._MIN_STABILITY:
            return None

        # Fallback parsers cap at 0.95 so a specific parser always wins ties.
        confidence = min(0.60 + best_ratio * 0.30, 0.95)
        return DetectedFormat(
            code=self.CODE,
            confidence=confidence,
            version="",
            notes=f"delim={best_delim!r}, stability={best_ratio:.2f}",
        )

    # ------------------------------------------------------------------ parse

    def parse(self, path: Path) -> ParserResult:
        path = Path(path)
        detected = self.detect(path)
        if detected is None:
            raise ParseError(
                f"CSVFallbackParser cannot parse {path.name!r}",
                path=path,
            )

        delim = _extract_delimiter(detected.notes)
        encoding = sniff_encoding(path)

        try:
            with path.open("r", encoding=encoding, errors="replace") as f:
                all_lines = [ln.rstrip("\r\n") for ln in f if ln.strip()]
        except OSError as exc:
            raise ParseError(
                f"Failed to read {path.name!r}: {exc}",
                path=path,
            ) from exc

        if not all_lines:
            raise ParseError(f"Empty file: {path.name!r}", path=path)

        header = all_lines[0].split(delim)
        rows = [ln.split(delim) for ln in all_lines[1:]]

        warnings: list[str] = []
        for i, row in enumerate(rows, start=2):  # line numbers are 1-indexed; header is 1
            if len(row) != len(header):
                warnings.append(
                    f"line {i}: column count {len(row)} != header {len(header)}"
                )
                if len(warnings) >= 5:
                    warnings.append("...(truncated)")
                    break

        payload = CSVPayload(
            header=header,
            rows=rows,
            encoding=encoding,
            delimiter=delim,
        )
        return ParserResult(
            payload=payload,
            source_path=path,
            detected=detected,
            warnings=warnings,
            metadata={
                "row_count": len(rows),
                "column_count": len(header),
            },
        )


def _extract_delimiter(notes: str) -> str:
    """
    Extract the delimiter literal from a detect() `notes` string.

    notes format: ``delim='X', stability=0.95`` where X is a single char that
    may itself be a comma — we must not terminate on the first comma.
    """
    prefix = "delim="
    start = notes.find(prefix)
    if start < 0:
        return ","
    # After the prefix we expect a quoted value: 'X'  (X may be a comma or \t)
    quoted = notes[start + len(prefix):]
    if not quoted.startswith("'"):
        # Unquoted fallback — read until "," (shouldn't normally happen)
        end = quoted.find(",")
        value = quoted[:end] if end >= 0 else quoted
        value = value.strip()
    else:
        # Find matching closing quote (quoted[0] is the opening ')
        end_quote = quoted.find("'", 1)
        value = quoted[1:end_quote] if end_quote > 0 else quoted[1:]
    # Decode python-literal escapes: "\\t" → "\t", "\\n" → "\n"
    if "\\" in value:
        try:
            return value.encode("utf-8").decode("unicode_escape")
        except UnicodeDecodeError:
            pass
    return value
