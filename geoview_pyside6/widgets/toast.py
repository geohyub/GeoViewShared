"""
GeoView Toast Notification
===========================
Non-blocking toast messages that auto-dismiss with:
- Drop shadow (level 2)
- Countdown progress bar
- Stacking (multiple toasts stack vertically)
- Close button
- Icon prefix (status icons)
"""

from __future__ import annotations

from typing import ClassVar

from PySide6.QtWidgets import (
    QFrame, QLabel, QHBoxLayout, QVBoxLayout, QWidget,
    QGraphicsOpacityEffect, QGraphicsDropShadowEffect,
)
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QSize
from PySide6.QtGui import QColor, QMouseEvent

from geoview_pyside6.constants import Font, Space, Radius, STATUS_ICONS
from geoview_pyside6.theme_aware import c


# ── Icon mapping for toast types ──────────────────────────────────
_TOAST_ICONS: dict[str, str] = {
    "success": STATUS_ICONS["PASS"],      # checkmark
    "warning": STATUS_ICONS["WARNING"],   # warning sign
    "error":   STATUS_ICONS["ERROR"],     # cross mark
    "info":    STATUS_ICONS["INFO"],      # info symbol
}


class _CountdownBar(QFrame):
    """A thin horizontal bar that shrinks from full width to zero."""

    def __init__(self, color: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFixedHeight(2)
        self._color = color
        self.setStyleSheet(f"""
            QFrame {{
                background: {color};
                border: none;
                border-radius: 1px;
            }}
        """)

    def start(self, duration_ms: int):
        """Animate maximumWidth from parent width to 0 over *duration_ms*."""
        start_w = self.parent().width() if self.parent() else 400
        self.setMaximumWidth(start_w)
        self._anim = QPropertyAnimation(self, b"maximumWidth", self)
        self._anim.setDuration(duration_ms)
        self._anim.setStartValue(start_w)
        self._anim.setEndValue(0)
        self._anim.setEasingCurve(QEasingCurve.Type.Linear)
        self._anim.start()


class _CloseLabel(QLabel):
    """A small clickable 'x' label."""

    def __init__(self, color: str, parent: QWidget | None = None):
        super().__init__("\u00D7", parent)  # multiplication sign as close glyph
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(18, 18)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet(f"""
            QLabel {{
                color: {c().MUTED};
                font-size: 15px;
                font-weight: 700;
                font-family: "{Font.SANS}";
                background: transparent;
                border: none;
                border-radius: 9px;
                padding: 0;
            }}
            QLabel:hover {{
                color: {color};
                background: {color}1A;
            }}
        """)

    def mousePressEvent(self, ev: QMouseEvent):
        """Walk up to the owning Toast and close it."""
        widget = self.parent()
        while widget and not isinstance(widget, Toast):
            widget = widget.parent()
        if widget:
            widget.close_toast()


class Toast(QFrame):
    """Auto-dismissing toast notification with shadow, countdown, stacking,
    close button, and icon prefix.

    Architecture note:
      Qt allows only ONE QGraphicsEffect per widget.  We need both a
      drop-shadow and an opacity fade-out.  Solution: the Toast (outer QFrame)
      carries the QGraphicsOpacityEffect for the fade animation.  An inner
      QFrame (_card) carries the QGraphicsDropShadowEffect for depth.
      This way both effects coexist without conflict.
    """

    # ── Class-level toast stack ───────────────────────────────────
    _active_toasts: ClassVar[list[Toast]] = []

    @staticmethod
    def _get_colors() -> dict[str, tuple[str, str]]:
        return {
            "success": (c().GREEN, f"{c().GREEN}1A"),
            "warning": (c().ORANGE, f"{c().ORANGE}1A"),
            "error":   (c().RED, f"{c().RED}1A"),
            "info":    (c().CYAN, f"{c().CYAN}1A"),
        }

    _MARGIN_TOP: ClassVar[int] = 16
    _GAP: ClassVar[int] = 8
    _MARGIN_RIGHT: ClassVar[int] = 20

    # ─────────────────────────────────────────────────────────────
    def __init__(
        self,
        message: str,
        toast_type: str = "info",
        duration: int = 3000,
        closable: bool = True,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.setObjectName("gv_toast_wrapper")
        self._toast_type = toast_type
        self._duration = duration
        self._closing = False

        _colors = self._get_colors()
        fg, _bg = _colors.get(toast_type, _colors["info"])
        self._fg = fg

        # ── Outer wrapper — transparent, holds the opacity effect ─
        self.setStyleSheet("QFrame#gv_toast_wrapper { background: transparent; border: none; }")

        # Opacity effect on the wrapper (for fade-out)
        self._opacity = QGraphicsOpacityEffect(self)
        self._opacity.setOpacity(1.0)
        self.setGraphicsEffect(self._opacity)

        wrapper_layout = QVBoxLayout(self)
        wrapper_layout.setContentsMargins(8, 4, 8, 8)  # room for shadow to render
        wrapper_layout.setSpacing(0)

        # ── Inner card — visible toast surface ───────────────────
        card = QFrame(self)
        card.setObjectName("gv_toast_card")
        card.setStyleSheet(f"""
            QFrame#gv_toast_card {{
                background: {c().NAVY};
                border: 1px solid {fg}40;
                border-left: 3px solid {fg};
                border-radius: {Radius.SM}px;
                min-width: 280px;
                max-width: 460px;
            }}
        """)

        # Shadow on the card (level 2 — dialog depth)
        shadow = QGraphicsDropShadowEffect(card)
        sc = QColor("#000000")
        sc.setAlpha(80)
        shadow.setColor(sc)
        shadow.setBlurRadius(20)
        shadow.setOffset(0, 4)
        card.setGraphicsEffect(shadow)

        # ── Card interior layout ─────────────────────────────────
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(Space.SM, Space.SM, Space.SM, 0)
        card_layout.setSpacing(0)

        # Content row: icon + message + close button
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, Space.SM)
        row.setSpacing(Space.SM)

        # Icon prefix
        icon_text = _TOAST_ICONS.get(toast_type, _TOAST_ICONS["info"])
        icon_lbl = QLabel(icon_text)
        icon_lbl.setFixedWidth(20)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignTop)
        icon_lbl.setStyleSheet(f"""
            QLabel {{
                color: {fg};
                font-size: {Font.BASE}px;
                font-family: "{Font.SANS}";
                background: transparent;
                border: none;
                padding: 0;
                padding-top: 1px;
            }}
        """)
        row.addWidget(icon_lbl)

        # Message label
        msg_lbl = QLabel(message)
        msg_lbl.setWordWrap(True)
        msg_lbl.setStyleSheet(f"""
            QLabel {{
                color: {fg};
                font-size: {Font.SM}px;
                font-family: "{Font.SANS}";
                background: transparent;
                border: none;
                padding: 0;
            }}
        """)
        row.addWidget(msg_lbl, stretch=1)

        # Close button
        if closable:
            self._close_btn = _CloseLabel(fg, self)
            row.addWidget(self._close_btn, alignment=Qt.AlignmentFlag.AlignTop)

        card_layout.addLayout(row)

        # Countdown bar
        self._countdown = _CountdownBar(fg, card)
        card_layout.addWidget(self._countdown)

        wrapper_layout.addWidget(card)

        # ── Final setup ──────────────────────────────────────────
        self.adjustSize()
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)

        # Register and position
        Toast._active_toasts.append(self)
        self._reposition_all()

        self.show()
        self.raise_()

        # Start countdown bar
        self._countdown.start(duration)

        # Auto-dismiss timer
        QTimer.singleShot(duration, self._fade_out)

    # ── Positioning ──────────────────────────────────────────────

    @classmethod
    def _reposition_all(cls):
        """Recompute Y positions for every active toast, grouped by parent."""
        by_parent: dict[int, list[Toast]] = {}
        for t in cls._active_toasts:
            pid = id(t.parent()) if t.parent() else 0
            by_parent.setdefault(pid, []).append(t)

        for group in by_parent.values():
            y = cls._MARGIN_TOP
            for t in group:
                pw = t.parent().width() if t.parent() else 800
                w = t.sizeHint().width()
                x = pw - w - cls._MARGIN_RIGHT
                t.move(max(x, 4), y)
                y += t.sizeHint().height() + cls._GAP

    # ── Close / fade-out ─────────────────────────────────────────

    def close_toast(self):
        """Immediately close (called by close button or programmatically)."""
        if self._closing:
            return
        self._closing = True
        self._remove_and_cleanup()

    def _fade_out(self):
        """Animate opacity to 0, then remove."""
        if self._closing:
            return
        self._closing = True

        self._fade_anim = QPropertyAnimation(self._opacity, b"opacity", self)
        self._fade_anim.setDuration(400)
        self._fade_anim.setStartValue(1.0)
        self._fade_anim.setEndValue(0.0)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._fade_anim.finished.connect(self._remove_and_cleanup)
        self._fade_anim.start()

    def _remove_and_cleanup(self):
        """Remove from stack, reposition remaining toasts, delete self."""
        if self in Toast._active_toasts:
            Toast._active_toasts.remove(self)
        Toast._reposition_all()
        self.hide()
        self.deleteLater()

    # ── Size hint ────────────────────────────────────────────────

    def sizeHint(self) -> QSize:
        sh = super().sizeHint()
        w = max(296, min(476, sh.width()))  # 280+16 / 460+16 accounting for shadow margins
        return QSize(w, sh.height())
