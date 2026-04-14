"""
geoview_pyside6.parsers.registry
================================
ParserRegistry — routing + entry-point-style registration.

Design decisions:
 - **Instance-based over singleton**: 테스트에서 `ParserRegistry()` 로 신규 인스턴스
   생성하여 격리. 글로벌 편의는 `default_registry` 하나만 제공.
 - **Ordered dict**: Python 3.7+ 의 dict 순서 보장을 활용 — 등록 순서가
   탐지 우선순위 tiebreaker 가 됨 (confidence 가 같을 때).
 - **Duplicate rejection by default**: 같은 CODE 재등록 금지, `replace=True` 로
   명시적 override. 실수로 파서가 덮어쓰이는 것 방지.
 - **Protocol check at registration**: `isinstance(parser, BaseParser)` 로 즉시
   검증 → 잘못된 객체가 Registry 에 남아 나중에 AttributeError 나는 것 방지.
 - **Swallow detect() exceptions**: MagQC 교훈 #22 의 "score/issue 단일 경로"
   — 한 parser 의 버그가 전체 pipeline 을 중단시키지 않음. parse() 예외는 전파.

Phase A-1 A1.1 산출물.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, TypeVar

from geoview_pyside6.parsers.base import (
    BaseParser,
    DetectedFormat,
    ParserError,
    ParserResult,
)

__all__ = [
    "ParserRegistry",
    "RegistryError",
    "default_registry",
    "register_parser",
    "detect",
    "parse",
]


P = TypeVar("P", bound=BaseParser)


class RegistryError(ParserError):
    """Registry-level errors (duplicate / missing / protocol violation)."""


@dataclass
class ParserRegistry:
    """
    Ordered registry of BaseParser instances with detect/parse routing.

    Usage::

        from pathlib import Path
        from geoview_pyside6.parsers import ParserRegistry

        reg = ParserRegistry()
        reg.register(CPeTITv30Parser())
        reg.register(AGS4Parser())
        result = reg.parse(Path("jako.cpt"))
        # → auto-detect picks the highest-confidence match and runs .parse()

    Or via decorator with the default registry::

        from geoview_pyside6.parsers import register_parser

        @register_parser()
        class MyFormatParser:
            CODE = "my_fmt"
            DISPLAY_NAME = "My Format"
            def detect(self, path): ...
            def parse(self, path): ...
    """

    _parsers: dict[str, BaseParser] = field(default_factory=dict)

    # ------------------------------------------------------------------ register

    def register(self, parser: BaseParser, *, replace: bool = False) -> BaseParser:
        """
        Add a parser to the registry.

        Args:
            parser:  object conforming to the BaseParser protocol
            replace: allow overriding an existing CODE (default False)

        Raises:
            RegistryError: object does not conform, empty CODE, or duplicate without replace.
        """
        if not isinstance(parser, BaseParser):
            raise RegistryError(
                f"Object does not conform to BaseParser protocol: "
                f"{type(parser).__name__}"
            )
        code = getattr(parser, "CODE", "") or ""
        if not code:
            raise RegistryError(f"Parser CODE must not be empty: {parser!r}")
        if code in self._parsers and not replace:
            existing = self._parsers[code]
            raise RegistryError(
                f"Duplicate parser CODE {code!r}: "
                f"existing {type(existing).__name__}, new {type(parser).__name__}. "
                f"Pass replace=True to override."
            )
        self._parsers[code] = parser
        return parser

    def unregister(self, code: str) -> BaseParser:
        """Remove a parser by CODE. Raises RegistryError if not found."""
        if code not in self._parsers:
            raise RegistryError(f"Parser CODE not registered: {code!r}")
        return self._parsers.pop(code)

    def clear(self) -> None:
        """Remove all parsers. Intended for test teardown."""
        self._parsers.clear()

    def codes(self) -> list[str]:
        """Return registered parser CODEs in registration order."""
        return list(self._parsers.keys())

    def get(self, code: str) -> BaseParser:
        """Return parser by CODE. Raises RegistryError if not found."""
        try:
            return self._parsers[code]
        except KeyError as exc:
            raise RegistryError(f"Parser CODE not registered: {code!r}") from exc

    # ------------------------------------------------------------------ routing

    def detect(self, path: Path) -> list[DetectedFormat]:
        """
        Run all registered parsers' `detect()` and return matches sorted by
        confidence descending.

        Parsers whose `detect()` raises an exception are **silently skipped**
        so that one bad parser cannot break the pipeline for others
        (MagQC 교훈 #22 — 단일 경로 + 견고함).

        Args:
            path: file to probe

        Returns:
            List of DetectedFormat sorted confidence-desc. Empty list = no matches.

        Raises:
            RegistryError: path does not exist
        """
        path = Path(path)
        if not path.exists():
            raise RegistryError(f"Path does not exist: {path}", path=path)

        results: list[DetectedFormat] = []
        for parser in self._parsers.values():
            try:
                detected = parser.detect(path)
            except Exception:
                # Silent swallow — one broken parser shouldn't kill the pipeline.
                # Upstream logging hook can be added via geoview_pyside6.runtime later.
                continue
            if detected is not None:
                results.append(detected)
        results.sort(key=lambda d: d.confidence, reverse=True)
        return results

    def parse(self, path: Path, *, code: str | None = None) -> ParserResult:
        """
        Full detect → parse pipeline.

        If `code` is given, that specific parser is used (bypassing auto-detect).
        Otherwise the highest-confidence matching parser is selected.

        Args:
            path: file to parse
            code: force a specific parser CODE (optional)

        Returns:
            ParserResult from the winning parser.

        Raises:
            RegistryError: path missing, forced CODE unknown, or no parser matched
            ParseError:    winning parser raised during parse (propagated)
        """
        path = Path(path)
        if not path.exists():
            raise RegistryError(f"Path does not exist: {path}", path=path)

        if code is not None:
            parser = self.get(code)
            return parser.parse(path)

        detected = self.detect(path)
        if not detected:
            raise RegistryError(
                f"No parser matched {path.name!r}. "
                f"Registered: {self.codes()}",
                path=path,
            )
        winner_code = detected[0].code
        parser = self.get(winner_code)
        return parser.parse(path)

    # ------------------------------------------------------------------ dunder

    def __len__(self) -> int:
        return len(self._parsers)

    def __contains__(self, code: object) -> bool:
        return isinstance(code, str) and code in self._parsers

    def __iter__(self):
        return iter(self._parsers.values())


# ---------------------------------------------------------------------------
# Default registry + convenience functions
# ---------------------------------------------------------------------------


default_registry: ParserRegistry = ParserRegistry()


def register_parser(*, replace: bool = False) -> Callable[[type[P]], type[P]]:
    """
    Class decorator registering an instance of `cls()` in the default registry.

    Usage::

        from geoview_pyside6.parsers import register_parser

        @register_parser()
        class CPeTITv30Parser:
            CODE = "cpet_it_v30"
            DISPLAY_NAME = "CPeT-IT Project (v30)"
            def detect(self, path): ...
            def parse(self, path): ...

    The decorator returns the class unchanged so ``cls()`` remains importable
    and testable.  Instantiation happens once at decoration time.

    Args:
        replace: pass through to ParserRegistry.register
    """

    def _decorator(cls: type[P]) -> type[P]:
        default_registry.register(cls(), replace=replace)
        return cls

    return _decorator


def detect(path: Path) -> list[DetectedFormat]:
    """Default-registry convenience: probe all registered parsers."""
    return default_registry.detect(path)


def parse(path: Path, *, code: str | None = None) -> ParserResult:
    """Default-registry convenience: full detect+parse pipeline."""
    return default_registry.parse(path, code=code)
