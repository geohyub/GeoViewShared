"""
geoview_pyside6.reports.builder
================================
:class:`ReportBuilder` — shared façade over the cross-domain report
generators in ``geoview_common.qc.common.report_builder``.

Design:
 - **Do not reimplement** the Excel/Word/PDF renderers. They are mature
   (964 lines, battle-tested in MagQC/SonarQC/SeismicQC). This module
   delegates to them and adds infrastructure — atomic writes, manifests,
   and a one-call triple-format entry point.
 - The underlying generators accept ``output_path=None`` and return
   :class:`io.BytesIO`. The builder always uses that mode so it owns
   the on-disk write step via :func:`geoview_pyside6.io_safe.atomic_writer`.
 - Each build call returns a :class:`ReportManifest` that downstream
   pack builders can serialize into the Deliverables Pack README.
"""
from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from enum import Enum
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING, Callable

from geoview_pyside6.io_safe import atomic_writer

if TYPE_CHECKING:
    from geoview_common.qc.common.models import QCProjectSummary

__all__ = [
    "ReportFormat",
    "ReportBuildError",
    "ReportArtifact",
    "ReportManifest",
    "ReportBuilder",
]


class ReportFormat(str, Enum):
    """Output formats supported by :class:`ReportBuilder`."""

    EXCEL = "xlsx"
    WORD = "docx"
    PDF = "pdf"


class ReportBuildError(Exception):
    """Raised when an underlying generator fails or produces empty bytes."""


@dataclass
class ReportArtifact:
    """Metadata for a single written report file."""

    format: ReportFormat
    path: Path
    size_bytes: int
    sha256: str


@dataclass
class ReportManifest:
    """Result of a :meth:`ReportBuilder.build_all` call."""

    base_name: str
    out_dir: Path
    artifacts: dict[ReportFormat, ReportArtifact] = field(default_factory=dict)
    duration_ms: float = 0.0

    @property
    def paths(self) -> dict[ReportFormat, Path]:
        return {fmt: art.path for fmt, art in self.artifacts.items()}

    def get(self, fmt: ReportFormat) -> ReportArtifact:
        try:
            return self.artifacts[fmt]
        except KeyError as exc:
            raise KeyError(
                f"{fmt.value!r} not built — available: "
                f"{[f.value for f in self.artifacts]}"
            ) from exc


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------


# Signature of the underlying generators in geoview_common.
_GeneratorFn = Callable[..., "BytesIO | Path"]


def _default_generators() -> dict[ReportFormat, _GeneratorFn]:
    # Import inside the function so tests can monkey-patch the module
    # without forcing openpyxl/docx/reportlab to load at collection time.
    from geoview_common.qc.common.report_builder import (
        generate_excel_report,
        generate_pdf_report,
        generate_word_report,
    )

    return {
        ReportFormat.EXCEL: generate_excel_report,
        ReportFormat.WORD: generate_word_report,
        ReportFormat.PDF: generate_pdf_report,
    }


@dataclass
class ReportBuilder:
    """
    One-call façade over the cross-domain report generators.

    Attributes:
        atomic:     route writes through io_safe.atomic_writer (default True).
        generators: dict mapping format → underlying generator function.
                    Defaults lazy-load from ``geoview_common``; tests inject
                    their own to avoid openpyxl/docx/reportlab at import time.
    """

    atomic: bool = True
    generators: dict[ReportFormat, _GeneratorFn] = field(default_factory=_default_generators)

    # ------------------------------------------------------------------
    # Single-format API
    # ------------------------------------------------------------------

    def build(
        self,
        summary: "QCProjectSummary",
        out_path: Path | str,
        *,
        fmt: ReportFormat,
    ) -> ReportArtifact:
        """Render ``summary`` as ``fmt`` at ``out_path``."""
        out = Path(out_path)
        if out.suffix.lower().lstrip(".") != fmt.value:
            raise ReportBuildError(
                f"out_path suffix {out.suffix!r} does not match format {fmt.value!r}"
            )
        out.parent.mkdir(parents=True, exist_ok=True)

        gen = self.generators.get(fmt)
        if gen is None:
            raise ReportBuildError(f"no generator registered for {fmt.value!r}")

        try:
            buf = gen(summary, output_path=None)
        except Exception as exc:
            raise ReportBuildError(
                f"{fmt.value} generator failed: {exc}"
            ) from exc

        data = self._to_bytes(buf, fmt)
        if not data:
            raise ReportBuildError(f"{fmt.value} generator produced empty output")

        self._write(out, data)
        digest = hashlib.sha256(data).hexdigest()
        return ReportArtifact(
            format=fmt,
            path=out.resolve(),
            size_bytes=len(data),
            sha256=digest,
        )

    def build_excel(self, summary, out_path) -> ReportArtifact:
        return self.build(summary, out_path, fmt=ReportFormat.EXCEL)

    def build_word(self, summary, out_path) -> ReportArtifact:
        return self.build(summary, out_path, fmt=ReportFormat.WORD)

    def build_pdf(self, summary, out_path) -> ReportArtifact:
        return self.build(summary, out_path, fmt=ReportFormat.PDF)

    # ------------------------------------------------------------------
    # Triple-format API
    # ------------------------------------------------------------------

    def build_all(
        self,
        summary: "QCProjectSummary",
        out_dir: Path | str,
        base_name: str,
        *,
        formats: tuple[ReportFormat, ...] = (
            ReportFormat.EXCEL,
            ReportFormat.WORD,
            ReportFormat.PDF,
        ),
    ) -> ReportManifest:
        """Render ``summary`` as every requested format into ``out_dir``."""
        if not base_name:
            raise ReportBuildError("base_name must not be empty")
        if any(sep in base_name for sep in ("/", "\\", "..")):
            raise ReportBuildError(f"base_name must be bare stem, got {base_name!r}")
        for bad in base_name:
            if bad in '<>:"|?*':
                raise ReportBuildError(
                    f"base_name contains reserved character {bad!r}: {base_name!r}"
                )

        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        t0 = time.perf_counter()
        manifest = ReportManifest(base_name=base_name, out_dir=out.resolve())

        for fmt in formats:
            target = out / f"{base_name}.{fmt.value}"
            manifest.artifacts[fmt] = self.build(summary, target, fmt=fmt)

        manifest.duration_ms = (time.perf_counter() - t0) * 1000.0
        return manifest

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _to_bytes(buf, fmt: ReportFormat) -> bytes:
        if isinstance(buf, BytesIO):
            return buf.getvalue()
        if isinstance(buf, (bytes, bytearray)):
            return bytes(buf)
        if isinstance(buf, Path):
            # Some generators may, surprisingly, write-and-return a path when
            # output_path=None is ignored. Read the file to keep the contract.
            return buf.read_bytes()
        raise ReportBuildError(
            f"{fmt.value} generator returned unsupported type "
            f"{type(buf).__name__}; expected BytesIO/bytes/Path"
        )

    def _write(self, path: Path, data: bytes) -> None:
        if not self.atomic:
            path.write_bytes(data)
            return
        with atomic_writer(path, mode="wb") as fh:
            fh.write(data)
