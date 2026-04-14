"""
Offscreen Qt fixture for geoview_pyside6.charts tests.

Sets ``QT_QPA_PLATFORM=offscreen`` before PySide6 loads and provides a
module-scoped ``qapp`` fixture. Import order matters: PySide6.QtWidgets
must resolve before ``pyqtgraph`` so pyqtgraph auto-detects the Qt binding.
"""
from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
