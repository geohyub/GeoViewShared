from __future__ import annotations

from pathlib import Path
from typing import Iterable


def _normalize_extensions(extensions: Iterable[str] | None) -> set[str] | None:
    if not extensions:
        return None
    return {
        ext.lower() if str(ext).startswith(".") else f".{str(ext).lower()}"
        for ext in extensions
    }


def _normalize_magic_bytes(magic_bytes: Iterable[bytes | bytearray | str] | None) -> list[bytes]:
    normalized: list[bytes] = []
    if not magic_bytes:
        return normalized
    for item in magic_bytes:
        if isinstance(item, bytes):
            normalized.append(item)
        elif isinstance(item, bytearray):
            normalized.append(bytes(item))
        else:
            normalized.append(str(item).encode("utf-8"))
    return [item for item in normalized if item]


def validate_file(
    path: str | Path,
    min_size: int = 0,
    extensions: Iterable[str] | None = None,
    magic_bytes: Iterable[bytes | bytearray | str] | None = None,
) -> tuple[bool, str]:
    """파일 유효성 검증. (valid, message) 반환."""
    file_path = Path(path)
    normalized_extensions = _normalize_extensions(extensions)
    normalized_magic = _normalize_magic_bytes(magic_bytes)

    if not file_path.exists():
        return False, f"파일이 존재하지 않습니다: {file_path}"
    if not file_path.is_file():
        return False, f"파일이 아닙니다: {file_path}"

    if normalized_extensions and file_path.suffix.lower() not in normalized_extensions:
        allowed = ", ".join(sorted(normalized_extensions))
        return False, f"허용되지 않은 확장자입니다: {file_path.suffix.lower()} (허용: {allowed})"

    size = file_path.stat().st_size
    if size == 0:
        return False, f"빈 파일입니다 (0 바이트): {file_path}"
    if min_size and size < min_size:
        return False, f"파일이 너무 작습니다 ({size} 바이트, 최소 {min_size} 바이트): {file_path}"

    if normalized_magic:
        header_size = max(len(item) for item in normalized_magic)
        header = file_path.read_bytes()[:header_size]
        if not any(header.startswith(prefix) for prefix in normalized_magic):
            return False, f"파일 헤더가 예상 포맷과 다릅니다: {file_path}"

    return True, ""


def validate_files(
    paths: Iterable[str | Path],
    min_size: int = 0,
    extensions: Iterable[str] | None = None,
    rules_by_extension: dict[str, dict] | None = None,
) -> tuple[list[str], list[tuple[str, str]]]:
    valid_paths: list[str] = []
    errors: list[tuple[str, str]] = []
    normalized_rules = {
        (ext.lower() if ext.startswith(".") else f".{ext.lower()}"): rule
        for ext, rule in (rules_by_extension or {}).items()
    }

    for original_path in paths:
        path_str = str(original_path)
        ext = Path(path_str).suffix.lower()
        rule = normalized_rules.get(ext, {})
        is_valid, message = validate_file(
            path_str,
            min_size=int(rule.get("min_size", min_size) or 0),
            extensions=rule.get("extensions", extensions),
            magic_bytes=rule.get("magic_bytes"),
        )
        if is_valid:
            valid_paths.append(path_str)
        else:
            errors.append((path_str, message))

    return valid_paths, errors
