"""
GeoView PySide6 — Notification Center
========================================
토스트 이력을 보관하고 표시하는 사이드 패널.
"""

from __future__ import annotations

from datetime import datetime
from typing import ClassVar

from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QWidget, QGraphicsOpacityEffect, QSizePolicy,
)
from PySide6.QtCore import (
    Qt, Signal, QPropertyAnimation, QEasingCurve, QTimer,
)

from geoview_pyside6.constants import Dark, Font, Space, Radius
from geoview_pyside6.theme_aware import c


# ── Level colors ──────────────────────────────────────────────

def _level_color(level: str) -> str:
    """Return the color for a notification level, respecting current theme."""
    _map = {
        "success": "GREEN",
        "warning": "ORANGE",
        "error":   "RED",
        "info":    "CYAN",
    }
    attr = _map.get(level, "CYAN")
    return getattr(c(), attr)


def _time_ago(dt: datetime) -> str:
    """Return human-readable relative time string."""
    now = datetime.now()
    diff = now - dt
    seconds = int(diff.total_seconds())

    if seconds < 60:
        return "Just now"
    elif seconds < 3600:
        mins = seconds // 60
        return f"{mins}m ago"
    elif seconds < 86400:
        hours = seconds // 3600
        return f"{hours}h ago"
    else:
        return dt.strftime("%m/%d %H:%M")


# ── Notification Item ─────────────────────────────────────────

class _NotificationItem(QFrame):
    """Single notification entry with level dot, timestamp, and message."""

    def __init__(self, data: dict, parent: QWidget | None = None):
        super().__init__(parent)
        self._data = data
        self.setStyleSheet(f"""
            QFrame {{
                background: transparent;
                border: none;
                border-bottom: 1px solid {c().BORDER};
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(Space.MD, Space.SM, Space.MD, Space.SM)
        layout.setSpacing(Space.SM)

        # Level dot
        level = data.get("level", "info")
        color = _level_color(level)

        dot = QLabel("\u25CF")  # filled circle
        dot.setFixedSize(16, 16)
        dot.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignTop)
        dot.setStyleSheet(f"""
            font-size: 8px;
            color: {color};
            background: transparent;
            padding-top: 4px;
        """)
        layout.addWidget(dot)

        # Text column
        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        text_col.setContentsMargins(0, 0, 0, 0)

        msg = QLabel(data.get("message", ""))
        msg.setWordWrap(True)
        msg.setStyleSheet(f"""
            font-size: {Font.SM}px;
            color: {c().TEXT};
            background: transparent;
        """)
        text_col.addWidget(msg)

        ts: datetime = data.get("timestamp", datetime.now())
        time_str = _time_ago(ts)
        time_lbl = QLabel(time_str)
        time_lbl.setStyleSheet(f"""
            font-size: {Font.XS}px;
            color: {c().DIM};
            background: transparent;
        """)
        text_col.addWidget(time_lbl)

        layout.addLayout(text_col, stretch=1)


# ── Empty State ───────────────────────────────────────────────

class _EmptyState(QFrame):
    """Placeholder shown when no notifications exist."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent; border: none;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, Space.XXXL, 0, Space.XXXL)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_lbl = QLabel("\u2014")  # em dash
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet(f"""
            font-size: {Font.XXL}px;
            color: {c().BORDER_H};
            background: transparent;
        """)
        layout.addWidget(icon_lbl)

        text_lbl = QLabel("No notifications")
        text_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text_lbl.setStyleSheet(f"""
            font-size: {Font.SM}px;
            color: {c().DIM};
            background: transparent;
        """)
        layout.addWidget(text_lbl)


# ── Notification Center ──────────────────────────────────────

class NotificationCenter(QFrame):
    """알림 이력 패널 (right-side overlay)."""

    unread_changed = Signal(int)  # emitted when unread count changes

    _PANEL_WIDTH = 320

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._history: list[dict] = []  # {timestamp, message, level}
        self._max_items = 100
        self._unread_count = 0

        self.setFixedWidth(self._PANEL_WIDTH)
        self.setObjectName("notificationCenter")
        self.setStyleSheet(f"""
            #notificationCenter {{
                background: {c().BG};
                border-left: 1px solid {c().BORDER};
            }}
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header ──
        header = QFrame()
        header.setFixedHeight(48)
        header.setStyleSheet(f"""
            QFrame {{
                background: {c().BG_ALT};
                border: none;
                border-bottom: 1px solid {c().BORDER};
            }}
        """)
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(Space.MD, 0, Space.SM, 0)
        h_layout.setSpacing(Space.SM)

        title = QLabel("Notifications")
        title.setStyleSheet(f"""
            font-size: {Font.MD}px;
            font-weight: {Font.MEDIUM};
            color: {c().TEXT_BRIGHT};
            background: transparent;
        """)
        h_layout.addWidget(title)

        # Unread badge
        self._badge = QLabel("0")
        self._badge.setFixedSize(22, 18)
        self._badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._badge.setStyleSheet(f"""
            font-size: {Font.XS}px;
            font-weight: {Font.BOLD};
            color: {c().BG};
            background: {c().CYAN};
            border-radius: 9px;
            padding: 0;
        """)
        self._badge.hide()
        h_layout.addWidget(self._badge)

        h_layout.addStretch()

        # Clear button
        clear_btn = QPushButton("Clear")
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {c().MUTED};
                border: none;
                font-size: {Font.XS}px;
                font-weight: {Font.MEDIUM};
                padding: 4px 10px;
                border-radius: {Radius.SM}px;
            }}
            QPushButton:hover {{
                background: {c().DARK};
                color: {c().TEXT};
            }}
        """)
        clear_btn.clicked.connect(self.clear)
        h_layout.addWidget(clear_btn)

        # Close button
        close_btn = QPushButton("\u00D7")
        close_btn.setFixedSize(28, 28)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {c().MUTED};
                border: none;
                border-radius: 14px;
                font-size: 16px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background: {c().SLATE};
                color: {c().TEXT};
            }}
        """)
        close_btn.clicked.connect(self._slide_out)
        h_layout.addWidget(close_btn)

        root.addWidget(header)

        # ── Scroll area ──
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setStyleSheet(f"""
            QScrollArea {{
                background: {c().BG};
                border: none;
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 5px;
                margin: 2px 0;
            }}
            QScrollBar::handle:vertical {{
                background: {c().BORDER_H};
                border-radius: 2px;
                min-height: 20px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
        """)

        self._list_widget = QWidget()
        self._list_widget.setStyleSheet("background: transparent;")
        self._list_layout = QVBoxLayout(self._list_widget)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(0)
        self._list_layout.addStretch()

        self._scroll.setWidget(self._list_widget)
        root.addWidget(self._scroll)

        # Empty state
        self._empty = _EmptyState()
        self._list_layout.insertWidget(0, self._empty)

    # ── Public API ────────────────────────────────────────

    def log(self, message: str, level: str = "info"):
        """알림 기록 추가."""
        entry = {
            "timestamp": datetime.now(),
            "message": message,
            "level": level,
        }
        self._history.insert(0, entry)
        if len(self._history) > self._max_items:
            self._history.pop()
        self._unread_count += 1
        self._rebuild_list()
        self._update_badge()
        self.unread_changed.emit(self._unread_count)

    def clear(self):
        """모든 알림 제거."""
        self._history.clear()
        self._unread_count = 0
        self._rebuild_list()
        self._update_badge()
        self.unread_changed.emit(0)

    def mark_read(self):
        """읽음 처리."""
        self._unread_count = 0
        self._update_badge()
        self.unread_changed.emit(0)

    @property
    def unread_count(self) -> int:
        return self._unread_count

    def toggle(self):
        """패널 표시/숨김 토글."""
        if self.isVisible():
            self._slide_out()
        else:
            self._slide_in()

    # ── Internal ──────────────────────────────────────────

    def _rebuild_list(self):
        """Clear and re-populate the notification list."""
        # Remove all items except the stretch at the end
        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()

        if not self._history:
            self._empty = _EmptyState()
            self._list_layout.insertWidget(0, self._empty)
            return

        for i, entry in enumerate(self._history):
            notif = _NotificationItem(entry)
            self._list_layout.insertWidget(i, notif)

    def _update_badge(self):
        """Update the unread badge display."""
        if self._unread_count > 0:
            count_text = str(self._unread_count) if self._unread_count < 100 else "99+"
            self._badge.setText(count_text)
            self._badge.show()
        else:
            self._badge.hide()

    def _slide_in(self):
        """Show panel with slide-from-right animation."""
        self.mark_read()
        parent = self.parent()
        if parent:
            h = parent.height()
            self.setFixedHeight(h)
            self.move(parent.width(), 0)

        self.show()
        self.raise_()

        if parent:
            target_x = parent.width() - self._PANEL_WIDTH
            self._anim = QPropertyAnimation(self, b"pos", self)
            self._anim.setDuration(200)
            self._anim.setStartValue(self.pos())
            from PySide6.QtCore import QPoint
            self._anim.setEndValue(QPoint(target_x, 0))
            self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            self._anim.start()

    def _slide_out(self):
        """Hide panel with slide-to-right animation."""
        parent = self.parent()
        if parent:
            target_x = parent.width()
            self._anim = QPropertyAnimation(self, b"pos", self)
            self._anim.setDuration(200)
            self._anim.setStartValue(self.pos())
            from PySide6.QtCore import QPoint
            self._anim.setEndValue(QPoint(target_x, 0))
            self._anim.setEasingCurve(QEasingCurve.Type.InCubic)
            self._anim.finished.connect(self.hide)
            self._anim.start()
        else:
            self.hide()
