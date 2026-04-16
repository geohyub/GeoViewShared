from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_SHARED_ROOT = Path(__file__).resolve().parents[2]
if str(_SHARED_ROOT) not in sys.path:
    sys.path.insert(0, str(_SHARED_ROOT))

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLabel, QScrollArea, QVBoxLayout, QWidget

from geoview_pyside6 import Category, GeoViewApp
from geoview_pyside6.widgets.file_drop_zone import FileDropZone


def _qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_setup_logging_writes_log_file_under_geoview_home(tmp_path, monkeypatch):
    monkeypatch.setenv("GEOVIEW_HOME", str(tmp_path / ".geoview"))

    logger = GeoViewApp.setup_logging("RuntimeInfraTest")
    logger.info("runtime logging smoke")
    for handler in logger.handlers:
        flush = getattr(handler, "flush", None)
        if flush:
            flush()

    log_file = tmp_path / ".geoview" / "logs" / "RuntimeInfraTest.log"
    assert log_file.exists()
    assert "runtime logging smoke" in log_file.read_text(encoding="utf-8")


def test_setup_logging_routes_module_loggers_to_same_log_file(tmp_path, monkeypatch):
    monkeypatch.setenv("GEOVIEW_HOME", str(tmp_path / ".geoview"))

    logger = GeoViewApp.setup_logging("RuntimeModuleLoggerTest")
    logging.getLogger("tests.runtime.module").info("module logging smoke")
    for handler in logger.handlers:
        flush = getattr(handler, "flush", None)
        if flush:
            flush()

    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        flush = getattr(handler, "flush", None)
        if flush:
            flush()

    log_file = tmp_path / ".geoview" / "logs" / "RuntimeModuleLoggerTest.log"
    assert log_file.exists()
    assert "module logging smoke" in log_file.read_text(encoding="utf-8")


def test_geoview_app_initializes_logger_and_settings(tmp_path, monkeypatch):
    monkeypatch.setenv("GEOVIEW_HOME", str(tmp_path / ".geoview"))
    _qapp()

    class DemoApp(GeoViewApp):
        APP_NAME = "RuntimeDemo"
        APP_VERSION = "v0.1"
        CATEGORY = Category.UTILITIES

        def setup_panels(self):
            self.add_panel("home", "H", "Home", QLabel("body"))

    app = DemoApp()
    try:
        assert app._settings is not None
        assert app._logger.name == "RuntimeDemo"
    finally:
        app.close()


def test_geoview_app_hardens_panel_surface_and_scroll_viewports(tmp_path, monkeypatch):
    monkeypatch.setenv("GEOVIEW_HOME", str(tmp_path / ".geoview"))
    _qapp()

    panel_root = QWidget()
    layout = QVBoxLayout(panel_root)
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll_body = QWidget()
    scroll.setWidget(scroll_body)
    layout.addWidget(scroll)

    class DemoApp(GeoViewApp):
        APP_NAME = "SurfaceDemo"
        APP_VERSION = "v0.1"
        CATEGORY = Category.UTILITIES

        def setup_panels(self):
            self.add_panel("home", "H", "Home", panel_root)

    app = DemoApp()
    try:
        assert panel_root.property("gvSurfaceRole") == "page"
        assert scroll.viewport().property("gvSurfaceRole") == "scroll-viewport"
        assert scroll.viewport().testAttribute(Qt.WidgetAttribute.WA_StyledBackground)
    finally:
        app.close()


def test_file_drop_zone_filters_invalid_files_with_rules(tmp_path):
    _qapp()
    valid = tmp_path / "line.xtf"
    valid.write_bytes(b"\x01" + (b"\x00" * 2048))

    invalid = tmp_path / "broken.xtf"
    invalid.write_bytes(b"")

    zone = FileDropZone(
        accepted_extensions={".xtf"},
        title="Drop XTF files",
        min_size=1024,
        validation_rules={".xtf": {"magic_bytes": [b"\x01"]}},
    )
    try:
        valid_paths, errors = zone.validate_paths([str(valid), str(invalid)])
        assert valid_paths == [str(valid)]
        assert len(errors) == 1
        assert errors[0][0] == str(invalid)
        assert "빈 파일" in errors[0][1]
    finally:
        zone.close()


def test_file_drop_zone_compatibility_setters_update_visible_text():
    _qapp()
    zone = FileDropZone(title="Original", browse_enabled=True, compact=True)
    try:
        zone.set_label_text("Updated Label")
        zone.set_browse_text("Pick File")

        assert zone._title_label.text() == "Updated Label"
        assert zone._browse_btn.text() == "Pick File"
        assert zone.accessibleName() == "Updated Label"
    finally:
        zone.close()
