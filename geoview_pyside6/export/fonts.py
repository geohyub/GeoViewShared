"""
geoview_pyside6.export.fonts
================================
Pretendard font registration for the matplotlib export pipeline.

Pretendard is distributed under SIL OFL 1.1 (verified Wave 0 — Q17) and
ships inside ``_shared/geoview_pyside6/fonts/``. This module:

 1. **Registers** all four weights with matplotlib's font manager so
    ``font.family = "Pretendard"`` resolves without platform-level install.
 2. **Configures rcParams** so vector exports keep text selectable:
     - ``svg.fonttype = "none"``  — text stays as `<text>` elements,
       editable in Illustrator / Inkscape, and the receiving PC can fall
       back to its installed Pretendard if the SVG is re-rendered.
     - ``pdf.fonttype = 42`` (TrueType embed) — Pretendard glyph outlines
       travel inside the PDF, so Korean never breaks on a client machine.
 3. Sets ``axes.unicode_minus = False`` so the minus sign renders as
    ASCII ``-`` (the default Unicode U+2212 glyph is missing from many
    Windows console/editor fonts).

Call :func:`register_pretendard` once per process. It is idempotent: the
second call is a no-op. Returns the family name string for convenience.
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

__all__ = [
    "PRETENDARD_FAMILY",
    "PRETENDARD_DIR",
    "PRETENDARD_FILES",
    "pretendard_available",
    "register_pretendard",
]


PRETENDARD_FAMILY = "Pretendard"
PRETENDARD_DIR = Path(__file__).resolve().parent.parent / "fonts"
PRETENDARD_FILES: tuple[str, ...] = (
    "Pretendard-Regular.otf",
    "Pretendard-Medium.otf",
    "Pretendard-SemiBold.otf",
    "Pretendard-Bold.otf",
)


_registered = False


def pretendard_available() -> bool:
    """Return True when every expected Pretendard OTF file is present."""
    return all((PRETENDARD_DIR / name).exists() for name in PRETENDARD_FILES)


def _iter_font_paths() -> Iterable[Path]:
    for name in PRETENDARD_FILES:
        p = PRETENDARD_DIR / name
        if p.exists():
            yield p


def register_pretendard(*, force: bool = False) -> str:
    """
    Register Pretendard with matplotlib's font manager and flip rcParams.

    Args:
        force: re-register even if a previous call already succeeded.
               Useful in tests that want a clean matplotlib state.

    Returns:
        The font family name (``"Pretendard"``).

    Raises:
        FileNotFoundError: when no Pretendard OTF files can be located.
    """
    global _registered
    if _registered and not force:
        return PRETENDARD_FAMILY

    import matplotlib
    from matplotlib import font_manager, rcParams

    paths = list(_iter_font_paths())
    if not paths:
        raise FileNotFoundError(
            f"no Pretendard font files under {PRETENDARD_DIR}"
        )

    for p in paths:
        font_manager.fontManager.addfont(str(p))

    rcParams["font.family"] = PRETENDARD_FAMILY
    rcParams["svg.fonttype"] = "none"   # text stays as <text>, not paths
    rcParams["pdf.fonttype"] = 42       # TrueType embed
    rcParams["axes.unicode_minus"] = False

    # Silence the "findfont: Generic family 'sans-serif' not found" warning
    # that some matplotlib configs emit before the cache refresh catches up.
    matplotlib.rcParams["font.sans-serif"] = [PRETENDARD_FAMILY] + list(
        matplotlib.rcParams.get("font.sans-serif", [])
    )

    _registered = True
    return PRETENDARD_FAMILY
