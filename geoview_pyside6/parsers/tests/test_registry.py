"""Tests for ParserRegistry routing + decorator + default registry."""
from __future__ import annotations

from pathlib import Path

import pytest

from geoview_pyside6.parsers.base import (
    DetectedFormat,
    ParseError,
    ParserResult,
)
from geoview_pyside6.parsers.registry import (
    ParserRegistry,
    RegistryError,
    default_registry,
    detect as global_detect,
    parse as global_parse,
    register_parser,
)


class AlphaParser:
    """Only detects .a files, high confidence."""

    CODE = "alpha"
    DISPLAY_NAME = "Alpha"

    def detect(self, path: Path):
        if path.suffix == ".a":
            return DetectedFormat(code=self.CODE, confidence=0.9)
        return None

    def parse(self, path: Path):
        return ParserResult(
            payload={"content": path.read_text(encoding="utf-8")},
            source_path=path,
            detected=DetectedFormat(code=self.CODE, confidence=0.9),
        )


class BetaParser:
    """Detects both .a and .b, lower confidence."""

    CODE = "beta"
    DISPLAY_NAME = "Beta"

    def detect(self, path: Path):
        if path.suffix in (".a", ".b"):
            return DetectedFormat(code=self.CODE, confidence=0.5)
        return None

    def parse(self, path: Path):
        return ParserResult(
            payload=None,
            source_path=path,
            detected=DetectedFormat(code=self.CODE, confidence=0.5),
        )


class ExplodingDetect:
    """Raises in detect() — must be swallowed by Registry."""

    CODE = "boom"
    DISPLAY_NAME = "Boom"

    def detect(self, path: Path):
        raise RuntimeError("kaboom")

    def parse(self, path: Path):
        raise ParseError("never reached")


@pytest.fixture
def reg() -> ParserRegistry:
    r = ParserRegistry()
    r.register(AlphaParser())
    r.register(BetaParser())
    return r


@pytest.fixture
def sample_a(tmp_path: Path) -> Path:
    p = tmp_path / "sample.a"
    p.write_text("hello", encoding="utf-8")
    return p


class TestRegister:
    def test_register_and_contains(self, reg: ParserRegistry):
        assert "alpha" in reg
        assert "beta" in reg
        assert len(reg) == 2

    def test_iter_returns_parsers(self, reg: ParserRegistry):
        codes = {p.CODE for p in reg}
        assert codes == {"alpha", "beta"}

    def test_duplicate_rejected(self, reg: ParserRegistry):
        with pytest.raises(RegistryError, match="Duplicate"):
            reg.register(AlphaParser())

    def test_replace_allowed(self, reg: ParserRegistry):
        new_alpha = AlphaParser()
        reg.register(new_alpha, replace=True)
        assert reg.get("alpha") is new_alpha

    def test_non_protocol_rejected(self):
        class Bad:
            pass

        r = ParserRegistry()
        with pytest.raises(RegistryError, match="conform"):
            r.register(Bad())  # type: ignore[arg-type]

    def test_empty_code_rejected(self):
        class EmptyCode:
            CODE = ""
            DISPLAY_NAME = "Empty"

            def detect(self, path):
                return None

            def parse(self, path):
                raise ParseError("no")

        r = ParserRegistry()
        with pytest.raises(RegistryError, match="must not be empty"):
            r.register(EmptyCode())

    def test_unregister(self, reg: ParserRegistry):
        removed = reg.unregister("alpha")
        assert removed.CODE == "alpha"
        assert "alpha" not in reg
        with pytest.raises(RegistryError):
            reg.unregister("alpha")

    def test_clear(self, reg: ParserRegistry):
        reg.clear()
        assert len(reg) == 0

    def test_codes_preserves_insertion_order(self, reg: ParserRegistry):
        assert reg.codes() == ["alpha", "beta"]

    def test_get_missing(self, reg: ParserRegistry):
        with pytest.raises(RegistryError, match="not registered"):
            reg.get("nope")


class TestDetect:
    def test_detect_returns_sorted_desc(self, reg: ParserRegistry, sample_a: Path):
        results = reg.detect(sample_a)
        assert len(results) == 2
        assert results[0].code == "alpha"  # 0.9
        assert results[1].code == "beta"  # 0.5

    def test_detect_no_match(self, reg: ParserRegistry, tmp_path: Path):
        p = tmp_path / "x.unknown"
        p.write_text("", encoding="utf-8")
        assert reg.detect(p) == []

    def test_detect_missing_file(self, reg: ParserRegistry, tmp_path: Path):
        with pytest.raises(RegistryError, match="does not exist"):
            reg.detect(tmp_path / "nope.txt")

    def test_detect_swallows_parser_exception(self, tmp_path: Path):
        r = ParserRegistry()
        r.register(AlphaParser())
        r.register(ExplodingDetect())
        sample = tmp_path / "f.a"
        sample.write_text("data", encoding="utf-8")
        results = r.detect(sample)
        # Alpha matches, ExplodingDetect swallowed
        assert len(results) == 1
        assert results[0].code == "alpha"


class TestParse:
    def test_parse_auto_detect(self, reg: ParserRegistry, sample_a: Path):
        result = reg.parse(sample_a)
        assert result.detected.code == "alpha"  # highest confidence wins
        assert result.payload == {"content": "hello"}

    def test_parse_forced_code(self, reg: ParserRegistry, sample_a: Path):
        result = reg.parse(sample_a, code="beta")
        assert result.detected.code == "beta"

    def test_parse_forced_unknown(self, reg: ParserRegistry, sample_a: Path):
        with pytest.raises(RegistryError, match="not registered"):
            reg.parse(sample_a, code="nope")

    def test_parse_no_match(self, reg: ParserRegistry, tmp_path: Path):
        p = tmp_path / "x.unknown"
        p.write_text("", encoding="utf-8")
        with pytest.raises(RegistryError, match="No parser matched"):
            reg.parse(p)

    def test_parse_missing_file(self, reg: ParserRegistry, tmp_path: Path):
        with pytest.raises(RegistryError, match="does not exist"):
            reg.parse(tmp_path / "gone.a")


class TestDecoratorAndGlobal:
    def test_register_parser_decorator(self, tmp_path: Path):
        # Clean test: add → verify → remove
        saved = list(default_registry.codes())

        @register_parser()
        class TempParser:
            CODE = "_test_temp_decorator"
            DISPLAY_NAME = "Temp"

            def detect(self, path):
                if path.suffix == ".temp":
                    return DetectedFormat(code=self.CODE, confidence=0.7)
                return None

            def parse(self, path):
                return ParserResult(
                    payload="ok",
                    source_path=path,
                    detected=DetectedFormat(code=self.CODE, confidence=0.7),
                )

        try:
            assert "_test_temp_decorator" in default_registry
            p = tmp_path / "x.temp"
            p.write_text("z", encoding="utf-8")
            results = global_detect(p)
            codes = [r.code for r in results]
            assert "_test_temp_decorator" in codes
            res = global_parse(p)
            assert res.payload == "ok"
        finally:
            default_registry.unregister("_test_temp_decorator")
            assert list(default_registry.codes()) == saved
