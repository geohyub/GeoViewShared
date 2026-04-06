"""
GeoView PySide6 — Settings Panel
==================================
앱 설정 다이얼로그: 외관, 단축키, 정보.
단일 스크롤 패널에 CollapsibleSection 그룹으로 구성.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QSlider, QComboBox, QPushButton, QScrollArea, QWidget,
    QApplication, QGraphicsOpacityEffect,
)
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve, QSize
from PySide6.QtGui import QFont, QKeySequence, QShortcut

from geoview_pyside6.constants import Dark, Font, Space, Radius
from geoview_pyside6.theme_aware import c
from geoview_pyside6 import effects
from geoview_pyside6.effects import apply_shadow


# ── Reusable row builder ──────────────────────────────────────

def _setting_row(label_text: str, control: QWidget, description: str = "") -> QWidget:
    """Build a single setting row: label on left, control on right, optional description below."""
    row = QFrame()
    row.setStyleSheet(f"""
        QFrame {{
            background: transparent;
            border: none;
            padding: 0;
        }}
    """)
    layout = QVBoxLayout(row)
    layout.setContentsMargins(Space.BASE, Space.SM, Space.BASE, Space.SM)
    layout.setSpacing(2)

    top = QHBoxLayout()
    top.setSpacing(Space.MD)

    lbl = QLabel(label_text)
    lbl.setStyleSheet(f"""
        font-size: {Font.SM}px;
        font-weight: {Font.MEDIUM};
        color: {c().TEXT};
        background: transparent;
    """)
    top.addWidget(lbl)
    top.addStretch()
    top.addWidget(control)

    layout.addLayout(top)

    if description:
        desc = QLabel(description)
        desc.setWordWrap(True)
        desc.setStyleSheet(f"""
            font-size: {Font.XS}px;
            color: {c().DIM};
            background: transparent;
            padding: 0;
        """)
        layout.addWidget(desc)

    return row


def _separator() -> QFrame:
    """Thin horizontal divider line."""
    line = QFrame()
    line.setFixedHeight(1)
    line.setStyleSheet(f"background: {c().BORDER}; border: none;")
    return line


# ── Toggle Switch ─────────────────────────────────────────────

class _ToggleSwitch(QPushButton):
    """Compact toggle switch that looks like a pill slider."""

    toggled_value = Signal(bool)

    def __init__(self, checked: bool = False, parent: QWidget | None = None):
        super().__init__(parent)
        self._checked = checked
        self.setFixedSize(44, 24)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clicked.connect(self._on_click)
        self._update_style()

    @property
    def is_checked(self) -> bool:
        return self._checked

    def set_checked(self, val: bool):
        self._checked = val
        self._update_style()

    def _on_click(self):
        self._checked = not self._checked
        self._update_style()
        self.toggled_value.emit(self._checked)

    def _update_style(self):
        if self._checked:
            self.setStyleSheet(f"""
                QPushButton {{
                    background: {c().GREEN};
                    border: none;
                    border-radius: 12px;
                    color: white;
                    font-size: 10px;
                    font-weight: 700;
                    text-align: right;
                    padding-right: 6px;
                }}
                QPushButton:hover {{ background: {c().GREEN_H}; }}
            """)
            self.setText("ON")
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background: {c().SLATE};
                    border: 1px solid {c().BORDER};
                    border-radius: 12px;
                    color: {c().DIM};
                    font-size: 10px;
                    font-weight: 700;
                    text-align: left;
                    padding-left: 6px;
                }}
                QPushButton:hover {{ background: {c().SURFACE}; }}
            """)
            self.setText("OFF")


# ── Section Header ────────────────────────────────────────────

class _SectionHeader(QFrame):
    """Clickable section header with chevron and title."""

    clicked = Signal()

    def __init__(self, title: str, expanded: bool = True, parent: QWidget | None = None):
        super().__init__(parent)
        self._expanded = expanded
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(40)
        self.setStyleSheet(f"""
            QFrame {{
                background: {c().DARK};
                border: none;
                border-radius: {Radius.SM}px;
            }}
            QFrame:hover {{ background: {c().NAVY}; }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(Space.MD, 0, Space.MD, 0)
        layout.setSpacing(Space.SM)

        self._chevron = QLabel()
        self._chevron.setFixedWidth(14)
        self._chevron.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._chevron.setStyleSheet(f"""
            font-size: {Font.XS}px;
            color: {c().MUTED};
            background: transparent;
        """)
        layout.addWidget(self._chevron)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"""
            font-size: {Font.SM}px;
            font-weight: {Font.SEMIBOLD};
            color: {c().TEXT};
            background: transparent;
            letter-spacing: 0.3px;
        """)
        layout.addWidget(title_lbl)
        layout.addStretch()

        self._update_chevron()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._expanded = not self._expanded
            self._update_chevron()
            self.clicked.emit()
        super().mousePressEvent(event)

    def _update_chevron(self):
        self._chevron.setText("\u25BC" if self._expanded else "\u25B6")


# ── Main Settings Dialog ─────────────────────────────────────

class SettingsPanel(QDialog):
    """앱 설정 다이얼로그."""

    settings_changed = Signal(dict)  # {key: value}

    def __init__(self, app_ref, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setFixedSize(520, 480)
        self._app = app_ref
        self.setWindowFlags(
            Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # ── Outer container with rounded bg ──
        self._container = QFrame(self)
        self._container.setObjectName("settingsContainer")
        self._container.setStyleSheet(f"""
            #settingsContainer {{
                background: {c().BG};
                border: 1px solid {c().BORDER};
                border-radius: {Radius.LG}px;
            }}
        """)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self._container)

        root = QVBoxLayout(self._container)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Dialog header ──
        header = QFrame()
        header.setFixedHeight(52)
        header.setStyleSheet(f"""
            QFrame {{
                background: {c().BG_ALT};
                border: none;
                border-top-left-radius: {Radius.LG}px;
                border-top-right-radius: {Radius.LG}px;
                border-bottom: 1px solid {c().BORDER};
            }}
        """)
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(Space.LG, 0, Space.MD, 0)

        title = QLabel("Settings")
        title.setStyleSheet(f"""
            font-size: {Font.MD}px;
            font-weight: {Font.SEMIBOLD};
            color: {c().TEXT_BRIGHT};
            background: transparent;
        """)
        h_layout.addWidget(title)
        h_layout.addStretch()

        close_btn = QPushButton("\u00D7")
        close_btn.setFixedSize(28, 28)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {c().MUTED};
                border: none;
                border-radius: 14px;
                font-size: 18px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background: {c().SLATE};
                color: {c().TEXT};
            }}
        """)
        close_btn.clicked.connect(self.close)
        h_layout.addWidget(close_btn)

        root.addWidget(header)

        # ── Scroll area ──
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                background: {c().BG};
                border: none;
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 6px;
                margin: 4px 0;
            }}
            QScrollBar::handle:vertical {{
                background: {c().BORDER_H};
                border-radius: 3px;
                min-height: 30px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
        """)

        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        self._content_layout = QVBoxLayout(scroll_content)
        self._content_layout.setContentsMargins(Space.LG, Space.MD, Space.LG, Space.LG)
        self._content_layout.setSpacing(Space.MD)

        # Build sections
        self._build_appearance_section()
        self._build_shortcuts_section()
        self._build_about_section()

        self._content_layout.addStretch()

        scroll.setWidget(scroll_content)
        root.addWidget(scroll)

        # Drop shadow
        apply_shadow(self._container, level=2)

        # Escape to close
        QShortcut(QKeySequence("Escape"), self, self.close)

    # ── Appearance ────────────────────────────────────────

    def _build_appearance_section(self):
        header = _SectionHeader("Appearance", expanded=True)
        self._content_layout.addWidget(header)

        body = QFrame()
        body.setStyleSheet("background: transparent; border: none;")
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        # Theme toggle
        is_dark = getattr(self._app, '_current_theme_mode', 'dark') == 'dark'
        self._theme_toggle = _ToggleSwitch(checked=is_dark)
        self._theme_toggle.toggled_value.connect(self._on_theme_toggle)
        body_layout.addWidget(
            _setting_row("Dark Mode", self._theme_toggle, "Toggle between dark and light theme")
        )
        body_layout.addWidget(_separator())

        # Language toggle
        is_ko = True
        if hasattr(self._app, 'lang_manager'):
            is_ko = self._app.lang_manager.lang == 'ko'
        self._lang_toggle = _ToggleSwitch(checked=is_ko)
        self._lang_toggle.toggled_value.connect(self._on_lang_toggle)

        lang_label = "Korean" if is_ko else "English"
        body_layout.addWidget(
            _setting_row("Korean Language", self._lang_toggle, f"Currently: {lang_label}")
        )
        body_layout.addWidget(_separator())

        # Font scale slider
        current_scale = 100
        if hasattr(self._app, '_settings'):
            current_scale = self._app._settings.value("font_scale", 100, type=int)

        slider_row = QFrame()
        slider_row.setStyleSheet("background: transparent; border: none;")
        sr_layout = QVBoxLayout(slider_row)
        sr_layout.setContentsMargins(Space.BASE, Space.SM, Space.BASE, Space.SM)
        sr_layout.setSpacing(4)

        top_row = QHBoxLayout()
        top_row.setSpacing(Space.MD)
        lbl = QLabel("Font Scale")
        lbl.setStyleSheet(f"""
            font-size: {Font.SM}px;
            font-weight: {Font.MEDIUM};
            color: {c().TEXT};
            background: transparent;
        """)
        top_row.addWidget(lbl)
        top_row.addStretch()

        self._scale_value = QLabel(f"{current_scale}%")
        self._scale_value.setFixedWidth(44)
        self._scale_value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._scale_value.setStyleSheet(f"""
            font-size: {Font.SM}px;
            font-weight: {Font.SEMIBOLD};
            color: {c().GREEN};
            background: transparent;
        """)
        top_row.addWidget(self._scale_value)
        sr_layout.addLayout(top_row)

        self._font_slider = QSlider(Qt.Orientation.Horizontal)
        self._font_slider.setRange(80, 150)
        self._font_slider.setValue(current_scale)
        self._font_slider.setTickInterval(10)
        self._font_slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                background: {c().SLATE};
                height: 4px;
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                background: {c().GREEN};
                width: 14px;
                height: 14px;
                margin: -5px 0;
                border-radius: 7px;
            }}
            QSlider::handle:horizontal:hover {{
                background: {c().GREEN_H};
            }}
            QSlider::sub-page:horizontal {{
                background: {c().GREEN};
                border-radius: 2px;
            }}
        """)
        self._font_slider.valueChanged.connect(self._on_font_scale_changed)
        sr_layout.addWidget(self._font_slider)

        range_row = QHBoxLayout()
        min_lbl = QLabel("80%")
        min_lbl.setStyleSheet(f"font-size: {Font.XS}px; color: {c().DIM}; background: transparent;")
        max_lbl = QLabel("150%")
        max_lbl.setStyleSheet(f"font-size: {Font.XS}px; color: {c().DIM}; background: transparent;")
        range_row.addWidget(min_lbl)
        range_row.addStretch()
        max_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        range_row.addWidget(max_lbl)
        sr_layout.addLayout(range_row)

        body_layout.addWidget(slider_row)
        body_layout.addWidget(_separator())

        # Reduce Motion toggle
        reduce_motion_on = False
        if hasattr(self._app, '_settings'):
            reduce_motion_on = self._app._settings.value("reduce_motion", False, type=bool)
        self._reduce_motion_toggle = _ToggleSwitch(checked=reduce_motion_on)
        self._reduce_motion_toggle.toggled_value.connect(self._on_reduce_motion_toggle)
        body_layout.addWidget(
            _setting_row(
                "Reduce Motion",
                self._reduce_motion_toggle,
                "Disable transition animations for accessibility",
            )
        )
        body_layout.addWidget(_separator())

        # Sound Effects toggle
        sound_on = True
        if hasattr(self._app, '_settings'):
            sound_on = self._app._settings.value("sound_enabled", True, type=bool)
        self._sound_toggle = _ToggleSwitch(checked=sound_on)
        self._sound_toggle.toggled_value.connect(self._on_sound_toggle)
        body_layout.addWidget(
            _setting_row(
                "Sound Effects",
                self._sound_toggle,
                "Play subtle sounds on actions and notifications",
            )
        )

        self._content_layout.addWidget(body)
        self._appearance_body = body

        header.clicked.connect(lambda: self._toggle_section(body))

    # ── Keyboard Shortcuts ────────────────────────────────

    def _build_shortcuts_section(self):
        header = _SectionHeader("Keyboard Shortcuts", expanded=True)
        self._content_layout.addWidget(header)

        body = QFrame()
        body.setStyleSheet("background: transparent; border: none;")
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        # Gather shortcuts from command palette
        shortcuts = [
            ("Command Palette", "Ctrl+Shift+P"),
            ("Go Home", "Ctrl+H"),
            ("Toggle Language", "Ctrl+L"),
            ("Toggle Theme", "Ctrl+Shift+T"),
            ("Fullscreen", "F11"),
            ("Open Settings", "Ctrl+,"),
        ]

        # Add any registered command palette actions that have shortcuts
        if hasattr(self._app, '_cmd_palette'):
            for action in self._app._cmd_palette._actions:
                if action.shortcut and action.shortcut not in [s[1] for s in shortcuts]:
                    shortcuts.append((action.label, action.shortcut))

        for i, (label, shortcut) in enumerate(shortcuts):
            row = QFrame()
            row.setStyleSheet("background: transparent; border: none;")
            r_layout = QHBoxLayout(row)
            r_layout.setContentsMargins(Space.BASE, Space.SM, Space.BASE, Space.SM)
            r_layout.setSpacing(Space.MD)

            name_lbl = QLabel(label)
            name_lbl.setStyleSheet(f"""
                font-size: {Font.SM}px;
                color: {c().TEXT};
                background: transparent;
            """)
            r_layout.addWidget(name_lbl)
            r_layout.addStretch()

            key_lbl = QLabel(shortcut)
            key_lbl.setStyleSheet(f"""
                font-size: {Font.XS}px;
                color: {c().MUTED};
                background: {c().DARK};
                border: 1px solid {c().BORDER};
                border-radius: 4px;
                padding: 2px 8px;
            """)
            r_layout.addWidget(key_lbl)

            body_layout.addWidget(row)

            if i < len(shortcuts) - 1:
                body_layout.addWidget(_separator())

        self._content_layout.addWidget(body)
        self._shortcuts_body = body

        header.clicked.connect(lambda: self._toggle_section(body))

    # ── About ─────────────────────────────────────────────

    def _build_about_section(self):
        header = _SectionHeader("About", expanded=True)
        self._content_layout.addWidget(header)

        body = QFrame()
        body.setStyleSheet("background: transparent; border: none;")
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(Space.BASE, Space.MD, Space.BASE, Space.MD)
        body_layout.setSpacing(Space.SM)

        app_name = getattr(self._app, 'APP_NAME', 'GeoView')
        app_version = getattr(self._app, 'APP_VERSION', 'v1.0.0')

        # App name + version
        name_lbl = QLabel(app_name)
        name_lbl.setStyleSheet(f"""
            font-size: {Font.LG}px;
            font-weight: {Font.BOLD};
            color: {c().TEXT_BRIGHT};
            background: transparent;
        """)
        body_layout.addWidget(name_lbl)

        ver_lbl = QLabel(app_version)
        ver_lbl.setStyleSheet(f"""
            font-size: {Font.SM}px;
            color: {c().MUTED};
            background: transparent;
        """)
        body_layout.addWidget(ver_lbl)

        body_layout.addSpacing(Space.SM)

        suite_lbl = QLabel("GeoView Suite")
        suite_lbl.setStyleSheet(f"""
            font-size: {Font.SM}px;
            color: {c().DIM};
            background: transparent;
        """)
        body_layout.addWidget(suite_lbl)

        powered_lbl = QLabel("Powered by PySide6")
        powered_lbl.setStyleSheet(f"""
            font-size: {Font.XS}px;
            color: {c().DIM};
            background: transparent;
        """)
        body_layout.addWidget(powered_lbl)

        self._content_layout.addWidget(body)
        self._about_body = body

        header.clicked.connect(lambda: self._toggle_section(body))

    # ── Section toggle ────────────────────────────────────

    def _toggle_section(self, body: QFrame):
        visible = body.isVisible()
        body.setVisible(not visible)

    # ── Callbacks ─────────────────────────────────────────

    def _on_theme_toggle(self, is_dark: bool):
        if hasattr(self._app, '_toggle_theme'):
            self._app._toggle_theme()
        self.settings_changed.emit({"theme_mode": "dark" if is_dark else "light"})

    def _on_lang_toggle(self, is_ko: bool):
        lang = "ko" if is_ko else "en"
        if hasattr(self._app, 'set_language'):
            self._app.set_language(lang)
        self.settings_changed.emit({"language": lang})

    def _on_reduce_motion_toggle(self, enabled: bool):
        effects.set_reduce_motion(enabled)
        if hasattr(self._app, '_settings'):
            self._app._settings.setValue("reduce_motion", enabled)
        self.settings_changed.emit({"reduce_motion": enabled})

    def _on_sound_toggle(self, enabled: bool):
        try:
            from geoview_pyside6.sounds import set_enabled
            set_enabled(enabled)
        except Exception:
            pass
        if hasattr(self._app, '_settings'):
            self._app._settings.setValue("sound_enabled", enabled)
        self.settings_changed.emit({"sound_enabled": enabled})

    def _on_font_scale_changed(self, value: int):
        self._scale_value.setText(f"{value}%")
        scale = value / 100.0
        base = int(Font.BASE * scale)
        app = QApplication.instance()
        if app:
            font = app.font()
            font.setPointSize(base)
            app.setFont(font)
        if hasattr(self._app, '_settings'):
            self._app._settings.setValue("font_scale", value)
        self.settings_changed.emit({"font_scale": value})

    # ── Override show to center on parent ─────────────────

    def showEvent(self, event):
        super().showEvent(event)
        if self.parent():
            p = self.parent()
            pg = p.mapToGlobal(p.rect().center())
            self.move(
                pg.x() - self.width() // 2,
                pg.y() - self.height() // 2,
            )
