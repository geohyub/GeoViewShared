"""
GeoView Icons — Lucide SVG Icon System
=======================================
사용법::

    from geoview_pyside6.icons import icon, icon_pixmap

    btn.setIcon(icon("anchor"))
    btn.setIcon(icon("compass", color="#095098"))
    pixmap = icon_pixmap("star", size=32, color="#10B981")
"""

from .icon_engine import icon, icon_pixmap, SvgIconEngine
from .app_icons import get_app_icon, set_app_icon

__all__ = ["icon", "icon_pixmap", "SvgIconEngine", "get_app_icon", "set_app_icon"]
