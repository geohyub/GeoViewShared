"""Regression tests for the shared GeoView i18n infra."""

from __future__ import annotations

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

SHARED_ROOT = os.path.dirname(os.path.dirname(__file__))
SHARED_PARENT = os.path.dirname(SHARED_ROOT)
if SHARED_PARENT not in sys.path:
    sys.path.insert(0, SHARED_PARENT)

from PySide6.QtWidgets import QApplication, QLabel

from geoview_pyside6 import Category, GeoViewApp, LanguageManager


def _qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_language_manager_register_and_toggle():
    manager = LanguageManager()
    seen: list[str] = []
    manager.language_changed.connect(seen.append)

    manager.register(
        {
            "ko": {"hello": "안녕하세요"},
            "en": {"hello": "Hello"},
        }
    )

    assert manager.lang == "ko"
    assert manager.t("hello") == "안녕하세요"
    assert manager.toggle() is True
    assert manager.lang == "en"
    assert manager.t("hello") == "Hello"
    assert seen == ["en"]


def test_geoview_app_exposes_language_controls_and_refresh_hook():
    _qapp()

    class DemoApp(GeoViewApp):
        APP_NAME = "Demo"
        APP_VERSION = "v0.1"
        CATEGORY = Category.UTILITIES

        def setup_panels(self):
            self.add_panel("home", "H", self.t("home_label", "Home"), QLabel("body"))
            self.register_translations(
                {
                    "ko": {"home_label": "홈"},
                    "en": {"home_label": "Home"},
                },
                refresh=True,
            )

        def on_language_changed(self, lang: str, force: bool = False) -> None:
            button = self.get_panel("home")
            if button is not None:
                self.sidebar.buttons[0].setText(self.t("home_label"))

    app = DemoApp()
    try:
        assert app.lang_manager.lang == "ko"
        assert app._lang_button is not None
        assert app._lang_button.text() == "KO"
        assert app.t("home_label") == "홈"

        app.set_language("en")
        assert app.lang_manager.lang == "en"
        assert app._lang_button.text() == "EN"
        assert app.sidebar.buttons[0].text() == "Home"
    finally:
        app.close()
