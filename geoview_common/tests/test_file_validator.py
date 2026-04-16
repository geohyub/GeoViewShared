from __future__ import annotations

import sys
from pathlib import Path

_SHARED_ROOT = Path(__file__).resolve().parents[2]
if str(_SHARED_ROOT) not in sys.path:
    sys.path.insert(0, str(_SHARED_ROOT))

from geoview_common.file_validator import validate_file, validate_files


def test_validate_file_rejects_missing_empty_and_too_small(tmp_path):
    missing = tmp_path / "missing.sgy"
    valid, message = validate_file(missing, min_size=3600, extensions={".sgy", ".segy"})
    assert valid is False
    assert "존재" in message

    empty = tmp_path / "empty.sgy"
    empty.write_bytes(b"")
    valid, message = validate_file(empty, min_size=3600, extensions={".sgy", ".segy"})
    assert valid is False
    assert "빈 파일" in message

    tiny = tmp_path / "tiny.sgy"
    tiny.write_bytes(b"\x00" * 120)
    valid, message = validate_file(tiny, min_size=3600, extensions={".sgy", ".segy"})
    assert valid is False
    assert "너무 작습니다" in message


def test_validate_file_checks_extension_and_magic_bytes(tmp_path):
    wrong_ext = tmp_path / "line.txt"
    wrong_ext.write_bytes(b"\x01" * 2048)
    valid, message = validate_file(
        wrong_ext,
        min_size=1024,
        extensions={".xtf"},
        magic_bytes=[b"\x01", b"\x00\x07"],
    )
    assert valid is False
    assert "확장자" in message

    wrong_magic = tmp_path / "line.xtf"
    wrong_magic.write_bytes(b"BAD!" + (b"\x00" * 2048))
    valid, message = validate_file(
        wrong_magic,
        min_size=1024,
        extensions={".xtf"},
        magic_bytes=[b"\x01", b"\x00\x07"],
    )
    assert valid is False
    assert "헤더" in message

    good = tmp_path / "line.xtf"
    good.write_bytes(b"\x01" + (b"\x00" * 2048))
    valid, message = validate_file(
        good,
        min_size=1024,
        extensions={".xtf"},
        magic_bytes=[b"\x01", b"\x00\x07"],
    )
    assert valid is True
    assert message == ""


def test_validate_files_returns_valid_paths_and_errors(tmp_path):
    valid_file = tmp_path / "survey.p190"
    valid_file.write_text("HEADER\n" + ("1" * 200), encoding="utf-8")
    bad_file = tmp_path / "empty.p190"
    bad_file.write_bytes(b"")

    valid_paths, errors = validate_files(
        [str(valid_file), str(bad_file)],
        min_size=100,
        extensions={".p190"},
    )

    assert valid_paths == [str(valid_file)]
    assert len(errors) == 1
    assert errors[0][0] == str(bad_file)
    assert "빈 파일" in errors[0][1]

