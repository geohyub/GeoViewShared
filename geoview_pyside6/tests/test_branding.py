"""Regression tests for branded app icons and splash rendering."""

from __future__ import annotations

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

SHARED_ROOT = os.path.dirname(os.path.dirname(__file__))
SHARED_PARENT = os.path.dirname(SHARED_ROOT)
if SHARED_PARENT not in sys.path:
    sys.path.insert(0, SHARED_PARENT)

from PySide6.QtWidgets import QApplication

from geoview_pyside6.branding import get_app_branding
from geoview_pyside6.constants import Category
from geoview_pyside6.icons import get_app_icon
from geoview_pyside6.splash import GeoViewSplash


def _qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_qc_branding_specs_exist_for_desktop_apps():
    expected = {
        "MagQC": "magnet",
        "SonarQC": "waves",
        "SeismicQC": "activity",
        "MBESQC": "layers",
        "NavQC": "navigation",
        "QCHub": "layout-dashboard",
    }
    for app_name, icon_name in expected.items():
        branding = get_app_branding(app_name, Category.QC)
        assert branding.icon_name == icon_name
        assert len(branding.features) >= 3
        assert branding.primary.startswith("#")


def test_branded_icons_render_for_qc_apps():
    _qapp()
    for app_name in ("MagQC", "SonarQC", "SeismicQC", "MBESQC", "NavQC", "QCHub"):
        qicon = get_app_icon(Category.QC, app_name=app_name)
        pixmap = qicon.pixmap(64, 64)
        assert not pixmap.isNull(), app_name


def test_splash_renders_with_cached_background():
    _qapp()
    splash = GeoViewSplash("NavQC", "v3.0", Category.QC)
    try:
        splash.set_status("Ready")
        pixmap = splash.pixmap()
        assert pixmap is not None
        assert not pixmap.isNull()
        assert splash._static_base.width() == pixmap.width()
    finally:
        splash.close()
