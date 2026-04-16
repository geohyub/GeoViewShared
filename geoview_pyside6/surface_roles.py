from __future__ import annotations

import re

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QScrollArea, QWidget

from geoview_pyside6.theme_aware import c

_SURFACE_BLOCK_RE = re.compile(
    r"/\* gv-surface:start \*/.*?/\* gv-surface:end \*/",
    re.DOTALL,
)


def _merge_surface_css(existing: str, css: str) -> str:
    base = _SURFACE_BLOCK_RE.sub("", existing or "").strip()
    block = f"/* gv-surface:start */\n{css}\n/* gv-surface:end */"
    return f"{base}\n{block}".strip() if base else block


def _repolish(widget: QWidget) -> None:
    style = widget.style()
    if style is not None:
        style.unpolish(widget)
        style.polish(widget)
    widget.update()


def _apply_surface(widget: QWidget | None, role: str, css: str) -> None:
    if widget is None:
        return
    widget.setProperty("gvSurfaceRole", role)
    widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    widget.setAutoFillBackground(False)
    widget.setStyleSheet(_merge_surface_css(widget.styleSheet(), css))
    _repolish(widget)


def harden_theme_surfaces(root: QWidget | None) -> None:
    """Fail closed so panel roots and QScrollArea internals do not flash native white."""
    if root is None:
        return

    _apply_surface(root, "page", f"background-color: {c().BG};")

    for scroll in root.findChildren(QScrollArea):
        _apply_surface(scroll, "scroll-shell", "background: transparent; border: none;")
        _apply_surface(scroll.viewport(), "scroll-viewport", "background: transparent; border: none;")
        _apply_surface(scroll.widget(), "scroll-content", "background: transparent; border: none;")
