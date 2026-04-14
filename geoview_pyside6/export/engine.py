"""
geoview_pyside6.export.engine
================================
:class:`VectorExportEngine` — turns a matplotlib ``Figure`` into the
SVG+PDF+PNG triple every deliverable plot needs.

Scope (A1.5 baseline):

 - **Input**: a ``matplotlib.figure.Figure``. Not a Qt widget — pyqtgraph's
   own SVG exporter is incompatible with Qt 6.11 (see ``charts/base.py``
   ``export_svg`` note), so the right abstraction is "build a Figure from
   the underlying data". CPT log plots, SBT charts and Robertson 9-zones
   should all be Figures that flow through this engine.

 - **Output**: three files in ``out_dir``::

       {base_name}.svg   — editable vector, selectable text (svg.fonttype=none)
       {base_name}.pdf   — print-ready vector with embedded TrueType fonts
       {base_name}.png   — raster at ``png_scale × dpi`` (default 2 × 150 = 300)

 - **Fonts**: :func:`register_pretendard` is called once per engine so the
   family resolves even on fresh clients.

 - **Color**: PNG gets sRGB stamped via :func:`ensure_srgb_png`.

 - **Atomicity**: all three formats are written through
   :func:`geoview_pyside6.io_safe.atomic_writer`, so a crash mid-render
   leaves no half-written files next to good ones.

 - **Return value**: :class:`ExportResult` carries absolute paths and
   the resolved font family, for downstream reporting / Deliverables Pack
   manifest generation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from geoview_pyside6.export.color import ensure_srgb_png
from geoview_pyside6.export.fonts import (
    PRETENDARD_FAMILY,
    register_pretendard,
)
from geoview_pyside6.io_safe import atomic_writer

if TYPE_CHECKING:
    from matplotlib.figure import Figure

__all__ = ["ExportError", "ExportResult", "VectorExportEngine"]


class ExportError(Exception):
    """Raised when a figure cannot be rendered to all three target formats."""


@dataclass
class ExportResult:
    """Result of a single :meth:`VectorExportEngine.render` call."""

    base_name: str
    out_dir: Path
    svg: Path
    pdf: Path
    png: Path
    dpi: int
    png_scale: float
    font_family: str = PRETENDARD_FAMILY
    extra: dict = field(default_factory=dict)

    @property
    def paths(self) -> dict[str, Path]:
        """All three output paths keyed by format suffix."""
        return {"svg": self.svg, "pdf": self.pdf, "png": self.png}


@dataclass
class VectorExportEngine:
    """
    Render matplotlib Figures into the SVG+PDF+PNG triple.

    Attributes:
        dpi:             base DPI for the PNG render. Vector outputs ignore
                         DPI except for their initial figure layout.
        png_scale:       multiplier applied on top of ``dpi`` for the PNG
                         raster — ``2.0`` default hits 300 DPI from a 150 DPI
                         figure, matching MagQC 교훈 #12 "@2x 인쇄 품질".
        register_font:   register Pretendard on first render (default True).
        atomic:          route writes through io_safe.atomic_writer
                         (default True).
    """

    dpi: int = 150
    png_scale: float = 2.0
    register_font: bool = True
    atomic: bool = True

    def __post_init__(self) -> None:
        if self.dpi <= 0:
            raise ValueError(f"dpi must be positive, got {self.dpi}")
        if self.png_scale <= 0:
            raise ValueError(f"png_scale must be positive, got {self.png_scale}")
        if self.register_font:
            register_pretendard()

    # ------------------------------------------------------------------

    def render(
        self,
        figure: "Figure",
        out_dir: Path | str,
        base_name: str,
    ) -> ExportResult:
        """
        Render ``figure`` as SVG + PDF + PNG into ``out_dir/base_name.{ext}``.

        Args:
            figure:    matplotlib ``Figure`` to render.
            out_dir:   directory (created if missing).
            base_name: file stem (no extension, no path separators).

        Returns:
            :class:`ExportResult` with absolute paths to all three files.
        """
        self._validate_inputs(figure, base_name)
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)

        svg_path = out / f"{base_name}.svg"
        pdf_path = out / f"{base_name}.pdf"
        png_path = out / f"{base_name}.png"

        png_dpi = int(round(self.dpi * self.png_scale))

        try:
            self._savefig(figure, svg_path, format="svg", dpi=self.dpi)
            self._savefig(figure, pdf_path, format="pdf", dpi=self.dpi)
            self._savefig(figure, png_path, format="png", dpi=png_dpi)
        except Exception as exc:
            raise ExportError(
                f"matplotlib savefig failed for {base_name!r}: {exc}"
            ) from exc

        ensure_srgb_png(png_path)

        return ExportResult(
            base_name=base_name,
            out_dir=out.resolve(),
            svg=svg_path.resolve(),
            pdf=pdf_path.resolve(),
            png=png_path.resolve(),
            dpi=self.dpi,
            png_scale=self.png_scale,
            extra={"png_dpi": png_dpi},
        )

    # ------------------------------------------------------------------

    @staticmethod
    def _validate_inputs(figure, base_name: str) -> None:
        # Lazy import so callers that only use fonts/color helpers don't pay
        # the matplotlib import tax.
        from matplotlib.figure import Figure

        if not isinstance(figure, Figure):
            raise TypeError(
                f"figure must be matplotlib.figure.Figure, got "
                f"{type(figure).__name__}"
            )
        if not base_name:
            raise ValueError("base_name must not be empty")
        if any(sep in base_name for sep in ("/", "\\", "..")):
            raise ValueError(
                f"base_name must be a bare file stem, got {base_name!r}"
            )
        for bad in base_name:
            if bad in '<>:"|?*':
                raise ValueError(
                    f"base_name contains reserved character {bad!r}: {base_name!r}"
                )

    def _savefig(self, figure, path: Path, *, format: str, dpi: int) -> None:
        if not self.atomic:
            figure.savefig(path, format=format, dpi=dpi, bbox_inches="tight")
            return
        mode = "w" if format == "svg" else "wb"
        with atomic_writer(path, mode=mode, encoding="utf-8" if mode == "w" else None) as fh:
            figure.savefig(fh, format=format, dpi=dpi, bbox_inches="tight")
