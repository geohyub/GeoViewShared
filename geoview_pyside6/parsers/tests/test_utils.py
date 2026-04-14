"""Tests for chunk_reader, first_n_lines, sniff_encoding."""
from __future__ import annotations

from pathlib import Path

import pytest

from geoview_pyside6.parsers.utils import (
    FIRST_N_LINES_DEFAULT,
    chunk_reader,
    first_n_lines,
    sniff_encoding,
)


@pytest.fixture
def tiny_utf8(tmp_path: Path) -> Path:
    p = tmp_path / "tiny.txt"
    p.write_text("hello world\nsecond line\n", encoding="utf-8")
    return p


@pytest.fixture
def many_lines(tmp_path: Path) -> Path:
    p = tmp_path / "many.txt"
    p.write_text(
        "\n".join(f"line {i}" for i in range(500)) + "\n",
        encoding="utf-8",
    )
    return p


class TestChunkReader:
    def test_reads_all_bytes(self, many_lines: Path):
        total = b""
        for chunk in chunk_reader(many_lines, chunk_size=128):
            assert isinstance(chunk, bytes)
            total += chunk
        assert total == many_lines.read_bytes()

    def test_text_mode(self, tiny_utf8: Path):
        chunks = list(chunk_reader(tiny_utf8, chunk_size=8, mode="r"))
        joined = "".join(c for c in chunks if isinstance(c, str))
        assert joined == tiny_utf8.read_text(encoding="utf-8")

    def test_invalid_mode(self, tiny_utf8: Path):
        with pytest.raises(ValueError, match="mode must be 'rb' or 'r'"):
            list(chunk_reader(tiny_utf8, mode="wb"))

    def test_empty_file(self, tmp_path: Path):
        p = tmp_path / "empty.txt"
        p.write_bytes(b"")
        assert list(chunk_reader(p)) == []


class TestFirstNLines:
    def test_default_constant(self):
        # MagQC 교훈 #21: 기본 200 줄
        assert FIRST_N_LINES_DEFAULT == 200

    def test_exact_count(self, many_lines: Path):
        lines = first_n_lines(many_lines, n=10)
        assert len(lines) == 10
        assert lines[0] == "line 0"
        assert lines[9] == "line 9"

    def test_less_available_than_requested(self, tiny_utf8: Path):
        lines = first_n_lines(tiny_utf8, n=50)
        assert lines == ["hello world", "second line"]

    def test_trailing_newline_stripped(self, tmp_path: Path):
        p = tmp_path / "x.txt"
        p.write_bytes(b"a\r\nb\r\nc\n")
        assert first_n_lines(p, n=10) == ["a", "b", "c"]

    def test_invalid_n(self, tiny_utf8: Path):
        with pytest.raises(ValueError, match="positive"):
            first_n_lines(tiny_utf8, n=0)
        with pytest.raises(ValueError, match="positive"):
            first_n_lines(tiny_utf8, n=-5)

    def test_default_applied(self, many_lines: Path):
        lines = first_n_lines(many_lines)
        assert len(lines) == FIRST_N_LINES_DEFAULT


class TestSniffEncoding:
    def test_plain_ascii(self, tmp_path: Path):
        p = tmp_path / "plain.txt"
        p.write_bytes(b"plain ascii only")
        assert sniff_encoding(p) == "utf-8"

    def test_utf8_bom(self, tmp_path: Path):
        p = tmp_path / "bom.txt"
        p.write_bytes(b"\xef\xbb\xbfwith bom")
        assert sniff_encoding(p) == "utf-8-sig"

    def test_cp949_korean(self, tmp_path: Path):
        p = tmp_path / "korean.txt"
        p.write_bytes("한글 텍스트 CP949".encode("cp949"))
        assert sniff_encoding(p) == "cp949"

    def test_utf8_korean(self, tmp_path: Path):
        p = tmp_path / "utf8k.txt"
        p.write_bytes("한글 UTF-8 텍스트".encode("utf-8"))
        assert sniff_encoding(p) == "utf-8"

    def test_utf16_le(self, tmp_path: Path):
        p = tmp_path / "u16le.txt"
        p.write_bytes(b"\xff\xfe" + "hi".encode("utf-16-le"))
        assert sniff_encoding(p) == "utf-16-le"

    def test_utf16_be(self, tmp_path: Path):
        p = tmp_path / "u16be.txt"
        p.write_bytes(b"\xfe\xff" + "hi".encode("utf-16-be"))
        assert sniff_encoding(p) == "utf-16-be"
