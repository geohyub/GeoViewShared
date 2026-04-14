"""
geoview_pyside6.parsers.utils
================================
Shared IO utilities for parsers.

Functions:
    chunk_reader(path, chunk_size, mode)
        Memory-safe streaming for multi-GB files.
    first_n_lines(path, n=200, encoding)
        Header peek used by detect() implementations.
        MagQC 교훈 #21: 50 줄로는 부족. 기본 200 줄.
    sniff_encoding(path)
        Lightweight encoding detection (BOM → UTF-8 → CP949 → latin-1).
        No chardet dependency — keep harness deps minimal.

Phase A-1 A1.1 산출물.
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterator

__all__ = [
    "chunk_reader",
    "first_n_lines",
    "sniff_encoding",
    "FIRST_N_LINES_DEFAULT",
]


# MagQC 교훈 #21: detect_format 검사 범위는 최소 100 줄. 기본 200 으로 여유.
FIRST_N_LINES_DEFAULT: int = 200

_CHUNK_DEFAULT_BYTES: int = 64 * 1024  # 64 KiB


def chunk_reader(
    path: Path,
    *,
    chunk_size: int = _CHUNK_DEFAULT_BYTES,
    mode: str = "rb",
) -> Iterator[bytes | str]:
    """
    Stream a file in fixed-size chunks. Memory-safe for multi-GB inputs.

    MagQC 교훈 #15 (대형 파일 del): 제너레이터는 현재 chunk 만 보유하므로
    소비자가 다음 chunk 를 요청하면 이전 chunk 가 GC 대상이 된다.

    Args:
        path:       source file
        chunk_size: bytes (mode='rb') or characters (mode='r')
        mode:       "rb" for bytes, "r" for text

    Yields:
        bytes or str chunks (depending on mode) until EOF.

    Raises:
        ValueError: invalid mode
        OSError:    file open failures (propagated)
    """
    if mode not in ("rb", "r"):
        raise ValueError(f"chunk_reader mode must be 'rb' or 'r', got {mode!r}")
    with path.open(mode) as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            yield chunk


def first_n_lines(
    path: Path,
    n: int = FIRST_N_LINES_DEFAULT,
    *,
    encoding: str | None = None,
    errors: str = "replace",
) -> list[str]:
    """
    Read up to `n` lines from the start of `path` with best-effort decoding.

    MagQC 교훈 #21: detect_format 은 50 줄로 부족. 헤더 긴 포맷
    (HELMS Vertek .cdf, CPeT-IT v30 base64 blob, AGS4 DICT 등) 을 위해
    기본 200 줄을 권장.

    Lines are stripped of trailing CR/LF but preserve interior whitespace.

    Args:
        path:     source file
        n:        maximum number of lines (> 0)
        encoding: forced codec, or None to auto-sniff via `sniff_encoding`
        errors:   Python codec error handler, default "replace"

    Returns:
        List of up to `n` decoded lines.

    Raises:
        ValueError: n <= 0
        OSError:    file open failures (propagated)
    """
    if n <= 0:
        raise ValueError(f"n must be positive, got {n}")
    enc = encoding or sniff_encoding(path)
    lines: list[str] = []
    with path.open("r", encoding=enc, errors=errors) as f:
        for i, line in enumerate(f):
            if i >= n:
                break
            lines.append(line.rstrip("\r\n"))
    return lines


_BOM_MARKS: tuple[tuple[bytes, str], ...] = (
    (b"\xef\xbb\xbf", "utf-8-sig"),
    (b"\xff\xfe\x00\x00", "utf-32-le"),
    (b"\x00\x00\xfe\xff", "utf-32-be"),
    (b"\xff\xfe", "utf-16-le"),
    (b"\xfe\xff", "utf-16-be"),
)


def sniff_encoding(path: Path, *, sample_bytes: int = 8192) -> str:
    """
    Lightweight encoding sniffer. BOM-first, then UTF-8 validation, then CP949 fallback.

    Returns a Python codec name suitable for `open(..., encoding=...)`.
    No external dependency (chardet 등) — GeoView 하네스는 의존성 최소화.

    Decision order:
        1. BOM magic bytes → utf-8-sig / utf-16-le / utf-16-be / utf-32-le / utf-32-be
        2. UTF-8 decode check (strict) → "utf-8"
        3. CP949 decode check → "cp949"  (국내 레거시 포맷 대응)
        4. Fallback → "latin-1"  (모든 바이트를 수용)

    For ambiguous inputs, callers (CPTPrep 임포트 마법사 B1.2/B1.3) should
    offer a user override.

    Args:
        path:         source file
        sample_bytes: how many leading bytes to inspect (default 8 KiB)

    Returns:
        Codec name string.
    """
    with path.open("rb") as f:
        head = f.read(sample_bytes)

    for mark, codec in _BOM_MARKS:
        if head.startswith(mark):
            return codec

    try:
        head.decode("utf-8")
        return "utf-8"
    except UnicodeDecodeError:
        pass

    try:
        head.decode("cp949")
        return "cp949"
    except UnicodeDecodeError:
        pass

    return "latin-1"
