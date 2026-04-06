"""
GeoView PySide6 — Welcome Dialog
===================================
첫 실행 환영 다이얼로그.
앱 기능 소개 + "다시 보지 않기" 옵션 제공.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QCheckBox, QWidget, QGridLayout, QFrame, QGraphicsOpacityEffect,
)
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QSettings
from PySide6.QtGui import QFont

from geoview_pyside6.constants import Dark, Font, Space, Radius
from geoview_pyside6.theme_aware import c


class WelcomeDialog(QDialog):
    """첫 실행 환영 다이얼로그."""

    def __init__(
        self,
        app_name: str,
        version: str = "",
        features: list[dict] | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.app_name = app_name
        self.dont_show_again = False

        self.setWindowTitle(f"Welcome to {app_name}")
        self.setFixedSize(560, 420)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Outer container for rounded background
        container = QFrame(self)
        container.setObjectName("welcomeContainer")
        container.setStyleSheet(f"""
            #welcomeContainer {{
                background: {c().BG_ALT};
                border: 1px solid {c().BORDER};
                border-radius: {Radius.LG}px;
            }}
        """)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(container)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(Space.XXL, Space.XXL, Space.XXL, Space.XL)
        layout.setSpacing(Space.LG)

        # ── Header: App name + version ──
        header_layout = QVBoxLayout()
        header_layout.setSpacing(Space.XS)

        # Accent color from parent if available
        accent = c().GREEN
        if parent and hasattr(parent, 'CATEGORY'):
            from geoview_pyside6.constants import CATEGORY_THEMES
            theme = CATEGORY_THEMES.get(parent.CATEGORY)
            if theme:
                accent = theme.accent

        name_label = QLabel(app_name)
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setStyleSheet(f"""
            font-size: {Font.XL}px;
            font-weight: {Font.BOLD};
            color: {accent};
            background: transparent;
        """)
        header_layout.addWidget(name_label)

        if version:
            ver_label = QLabel(version)
            ver_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            ver_label.setStyleSheet(f"""
                font-size: {Font.XS}px;
                color: {c().DIM};
                background: transparent;
            """)
            header_layout.addWidget(ver_label)

        layout.addLayout(header_layout)

        # ── Feature grid (2x2) ──
        if features:
            grid = QGridLayout()
            grid.setSpacing(Space.MD)

            for idx, feat in enumerate(features[:4]):
                card = self._make_feature_card(
                    feat.get("icon", ""),
                    feat.get("title", ""),
                    feat.get("desc", ""),
                    accent,
                )
                row = idx // 2
                col = idx % 2
                grid.addWidget(card, row, col)

            layout.addLayout(grid)
        else:
            # Spacer if no features
            layout.addStretch()

        layout.addStretch()

        # ── Bottom: checkbox + button ──
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(Space.MD)

        self._checkbox = QCheckBox("Don't show again")
        self._checkbox.setStyleSheet(f"""
            QCheckBox {{
                font-size: {Font.XS}px;
                color: {c().MUTED};
                background: transparent;
                spacing: {Space.XS}px;
            }}
            QCheckBox::indicator {{
                width: 14px;
                height: 14px;
                border: 1px solid {c().BORDER_H};
                border-radius: 3px;
                background: {c().DARK};
            }}
            QCheckBox::indicator:checked {{
                background: {accent};
                border-color: {accent};
            }}
        """)
        bottom_layout.addWidget(self._checkbox)

        bottom_layout.addStretch()

        btn = QPushButton("Get Started")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedHeight(36)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {accent};
                color: {c().BG};
                border: none;
                border-radius: {Radius.SM}px;
                font-size: {Font.SM}px;
                font-weight: {Font.SEMIBOLD};
                padding: 0 {Space.XL}px;
            }}
            QPushButton:hover {{
                opacity: 0.9;
            }}
        """)
        btn.clicked.connect(self._on_get_started)
        bottom_layout.addWidget(btn)

        layout.addLayout(bottom_layout)

        # Fade-in deferred to showEvent for consistency

    def showEvent(self, event):
        super().showEvent(event)
        effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(effect)
        effect.setOpacity(0.0)
        self._fade = QPropertyAnimation(effect, b"opacity", self)
        self._fade.setDuration(150)
        self._fade.setStartValue(0.0)
        self._fade.setEndValue(1.0)
        self._fade.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._fade.finished.connect(lambda: self.setGraphicsEffect(None))
        self._fade.start()

    def _make_feature_card(
        self, icon_text: str, title: str, desc: str, accent: str
    ) -> QFrame:
        """개별 기능 카드 위젯 생성."""
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background: {c().NAVY};
                border-radius: {Radius.SM}px;
                padding: {Space.MD}px;
            }}
        """)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(Space.MD, Space.MD, Space.MD, Space.MD)
        card_layout.setSpacing(Space.SM)

        # Icon (large text glyph)
        if icon_text:
            icon_label = QLabel(icon_text)
            icon_label.setStyleSheet(f"""
                font-size: 24px;
                color: {accent};
                background: transparent;
            """)
            card_layout.addWidget(icon_label)

        # Title
        if title:
            title_label = QLabel(title)
            title_label.setStyleSheet(f"""
                font-size: {Font.SM}px;
                font-weight: {Font.SEMIBOLD};
                color: {c().TEXT_BRIGHT};
                background: transparent;
            """)
            title_label.setWordWrap(True)
            card_layout.addWidget(title_label)

        # Description
        if desc:
            desc_label = QLabel(desc)
            desc_label.setStyleSheet(f"""
                font-size: {Font.XS}px;
                color: {c().MUTED};
                background: transparent;
                line-height: 1.3;
            """)
            desc_label.setWordWrap(True)
            card_layout.addWidget(desc_label)

        card_layout.addStretch()
        return card

    def _on_get_started(self) -> None:
        """Get Started 버튼 클릭 핸들러."""
        self.dont_show_again = self._checkbox.isChecked()
        self.accept()
