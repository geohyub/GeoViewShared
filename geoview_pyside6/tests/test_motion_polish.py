"""Regression tests for shared motion/detail polish."""

from __future__ import annotations

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

SHARED_ROOT = os.path.dirname(os.path.dirname(__file__))
SHARED_PARENT = os.path.dirname(SHARED_ROOT)
if SHARED_PARENT not in sys.path:
    sys.path.insert(0, SHARED_PARENT)

from PySide6.QtCore import QPoint, QEvent, qInstallMessageHandler
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget
from PySide6.QtCore import QParallelAnimationGroup

from geoview_pyside6.effects import _HoverLiftFilter, apply_shadow, reveal_widget
from geoview_pyside6.widgets import AnimatedStackedWidget, DashboardTemplate, KPICard


def _qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_reveal_widget_preserves_existing_shadow_effect():
    _qapp()
    widget = QWidget()
    widget.move(20, 24)
    shadow = apply_shadow(widget, level=1)
    reveal_widget(widget, offset_y=6, duration_ms=20)
    QTest.qWait(60)
    assert widget.graphicsEffect() is shadow
    assert widget.pos() == QPoint(20, 24)


def test_reveal_widget_safely_ignores_deleted_widget():
    _qapp()
    widget = QWidget()
    widget.show()
    widget.deleteLater()
    QTest.qWait(20)

    reveal_widget(widget, offset_y=6, duration_ms=20)


def test_reveal_widget_does_not_shift_layout_managed_widget():
    _qapp()
    host = QWidget()
    layout = QVBoxLayout(host)
    label = QLabel("hello")
    layout.addWidget(label)
    host.show()
    QTest.qWait(20)

    original = label.pos()
    reveal_widget(label, offset_y=10, duration_ms=20)
    QTest.qWait(60)

    assert label.pos() == original
    host.close()


def test_directional_stack_keeps_sidebar_navigation_stationary():
    _qapp()
    stack = AnimatedStackedWidget(duration=20)
    first = QWidget()
    second = QWidget()
    stack.addWidget(first)
    stack.addWidget(second)
    stack.resize(480, 320)
    stack.setCurrentWidget(first)
    stack.show()
    QTest.qWait(20)

    origin = first.pos()
    stack.set_current_with_animation(second, direction="forward")
    assert isinstance(stack._anim_group, QParallelAnimationGroup)
    assert second.pos() == origin

    QTest.qWait(80)
    assert stack.currentWidget() is second
    stack.close()


def test_directional_stack_transition_avoids_qpainter_warnings():
    _qapp()
    stack = AnimatedStackedWidget(duration=40)

    first = DashboardTemplate()
    first.add_kpi(KPICard("star", "1", "One"))
    first.set_toolbar(QLabel("Toolbar 1"))
    first.set_content(QWidget())
    first.set_footer(QLabel("Footer 1"))

    second = DashboardTemplate()
    second.add_kpi(KPICard("star", "2", "Two"))
    second.set_toolbar(QLabel("Toolbar 2"))
    second.set_content(QWidget())
    second.set_footer(QLabel("Footer 2"))

    stack.addWidget(first)
    stack.addWidget(second)
    stack.resize(640, 420)
    stack.setCurrentWidget(first)

    messages: list[str] = []

    def _handler(_msg_type, _context, message):
        messages.append(message)

    previous = qInstallMessageHandler(_handler)
    try:
        stack.show()
        QTest.qWait(120)
        messages.clear()

        stack.set_current_with_animation(second, direction="forward")
        QTest.qWait(180)
    finally:
        qInstallMessageHandler(previous)
        stack.close()

    painter_messages = [
        message
        for message in messages
        if "QPainter::" in message or "QWidgetEffectSourcePrivate::pixmap" in message
    ]
    assert painter_messages == []


def test_polished_cards_and_dashboard_reveal_on_first_show():
    _qapp()
    dashboard = DashboardTemplate()
    card = KPICard("star", "12", "Score")
    dashboard.add_kpi(card)
    dashboard.set_toolbar(QLabel("Toolbar"))
    dashboard.set_content(QWidget())
    dashboard.set_footer(QLabel("Footer"))

    dashboard.show()
    QTest.qWait(80)

    assert dashboard.property("gvSurfaceRole") == "page"
    assert hasattr(card, "_hover_lift_filter")
    assert card._revealed_once is True
    assert dashboard._revealed_once is True
    dashboard.close()


def test_hover_lift_filter_ignores_teardown_events_after_widget_reference_is_gone():
    _qapp()
    widget = QWidget()
    filt = _HoverLiftFilter(widget, lift_px=2)
    del filt._widget

    handled = filt.eventFilter(widget, QEvent(QEvent.Type.Enter))

    assert handled is False
