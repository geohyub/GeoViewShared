"""Tests for BaseParser Protocol, DetectedFormat, ParserResult, errors."""
from __future__ import annotations

from pathlib import Path

import pytest

from geoview_pyside6.parsers.base import (
    BaseParser,
    DetectedFormat,
    DetectError,
    ParseError,
    ParserError,
    ParserResult,
)


class TestDetectedFormat:
    def test_valid_construction(self):
        d = DetectedFormat(code="xyz", confidence=0.8, version="1.0", notes="test")
        assert d.code == "xyz"
        assert d.confidence == 0.8
        assert d.version == "1.0"
        assert d.notes == "test"

    def test_defaults(self):
        d = DetectedFormat(code="x", confidence=0.5)
        assert d.version == ""
        assert d.notes == ""

    def test_empty_code_rejected(self):
        with pytest.raises(ValueError, match="code must not be empty"):
            DetectedFormat(code="", confidence=0.5)

    def test_confidence_upper_bound(self):
        with pytest.raises(ValueError, match=r"\[0.0, 1.0\]"):
            DetectedFormat(code="x", confidence=1.5)

    def test_confidence_lower_bound(self):
        with pytest.raises(ValueError, match=r"\[0.0, 1.0\]"):
            DetectedFormat(code="x", confidence=-0.1)

    def test_boundary_values_allowed(self):
        DetectedFormat(code="x", confidence=0.0)
        DetectedFormat(code="x", confidence=1.0)

    def test_frozen(self):
        d = DetectedFormat(code="x", confidence=0.5)
        with pytest.raises(Exception):  # FrozenInstanceError
            d.code = "y"  # type: ignore[misc]


class TestParserResult:
    def test_default_fields(self, tmp_path: Path):
        d = DetectedFormat(code="x", confidence=0.5)
        r = ParserResult(
            payload=None,
            source_path=tmp_path / "f.txt",
            detected=d,
        )
        assert r.warnings == []
        assert r.errors == []
        assert r.metadata == {}
        assert r.ok is True

    def test_not_ok_when_errors(self, tmp_path: Path):
        d = DetectedFormat(code="x", confidence=0.5)
        r = ParserResult(
            payload=None,
            source_path=tmp_path / "f.txt",
            detected=d,
            errors=["boom"],
        )
        assert r.ok is False

    def test_warnings_do_not_affect_ok(self, tmp_path: Path):
        d = DetectedFormat(code="x", confidence=0.5)
        r = ParserResult(
            payload=None,
            source_path=tmp_path / "f.txt",
            detected=d,
            warnings=["minor issue"],
        )
        assert r.ok is True


class TestErrors:
    def test_hierarchy(self):
        assert issubclass(DetectError, ParserError)
        assert issubclass(ParseError, ParserError)
        assert issubclass(ParserError, Exception)

    def test_error_with_path(self, tmp_path: Path):
        err = ParserError("boom", path=tmp_path / "bad.txt")
        assert err.path == tmp_path / "bad.txt"
        assert "bad.txt" in str(err)
        assert "boom" in str(err)

    def test_error_without_path(self):
        err = ParserError("plain")
        assert err.path is None
        assert "path=" not in str(err)
        assert str(err) == "plain"

    def test_parse_error_subclass(self, tmp_path: Path):
        err = ParseError("parse failed", path=tmp_path / "x.csv")
        assert isinstance(err, ParserError)


class TestProtocol:
    def test_runtime_checkable_valid(self):
        class DummyParser:
            CODE = "dummy"
            DISPLAY_NAME = "Dummy"

            def detect(self, path):
                return None

            def parse(self, path):
                raise ParseError("no data")

        assert isinstance(DummyParser(), BaseParser)

    def test_missing_methods_rejected(self):
        class Incomplete:
            CODE = "incomplete"
            DISPLAY_NAME = "Incomplete"
            # missing detect + parse

        assert not isinstance(Incomplete(), BaseParser)

    def test_only_detect_missing(self):
        class NoDetect:
            CODE = "x"
            DISPLAY_NAME = "X"

            def parse(self, path):
                raise ParseError("no")

        assert not isinstance(NoDetect(), BaseParser)
