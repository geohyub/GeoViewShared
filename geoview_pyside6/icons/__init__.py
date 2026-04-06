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

__all__ = ["icon", "icon_pixmap", "SvgIconEngine"]
