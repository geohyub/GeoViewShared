from __future__ import annotations

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

SHARED_ROOT = os.path.dirname(os.path.dirname(__file__))
SHARED_PARENT = os.path.dirname(SHARED_ROOT)
if SHARED_PARENT not in sys.path:
    sys.path.insert(0, SHARED_PARENT)

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from geoview_pyside6.widgets.track_plot import LineRoute, TrackPlot


def _qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class _FakeClickEvent:
    def __init__(self, *, is_double: bool = False, modifiers=Qt.KeyboardModifier.NoModifier):
        self._is_double = is_double
        self._modifiers = modifiers

    def double(self):
        return self._is_double

    def modifiers(self):
        return self._modifiers


def test_track_plot_separates_selection_from_activation():
    _qapp()
    track = TrackPlot(show_legend=False, show_toolbar=False, show_hint=True)
    route = LineRoute(
        line_id=7,
        name="Line 07",
        lats=[0.0, 1.0, 2.0],
        lons=[10.0, 11.0, 12.0],
        score=82.0,
        grade="A",
        status="PASS",
    )
    track.set_routes([route])

    selected: list[object] = []
    activated: list[object] = []
    track.line_selected.connect(selected.append)
    track.line_activated.connect(activated.append)

    track._hovered_route = route
    track._on_mouse_clicked(_FakeClickEvent())

    assert selected == [7]
    assert activated == []
    assert track.get_selected_ids() == [7]

    track._hovered_route = route
    track._on_mouse_clicked(_FakeClickEvent(is_double=True))

    assert selected == [7, 7]
    assert activated == [7]
    track.close()


def test_track_plot_can_override_hint_text():
    _qapp()
    track = TrackPlot(show_legend=False, show_toolbar=False, show_hint=True)
    track.set_hint_text("Click to select. Double-click to open.")

    assert track._hint_label is not None
    assert track._hint_label.text() == "Click to select. Double-click to open."
    track.close()
