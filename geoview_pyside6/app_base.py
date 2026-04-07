"""
GeoView PySide6 — Base Application
====================================
모든 GeoView 프로그램이 상속하는 QMainWindow 기반 클래스.
사이드바 + 콘텐츠 + 상태바 레이아웃을 기본 제공.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QMainWindow, QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QStackedWidget, QLabel, QPushButton, QFrame, QSizePolicy,
    QStatusBar, QToolButton, QMenu, QSplitter, QDockWidget,
)
from PySide6.QtCore import Qt, QSize, Signal, QSettings
from PySide6.QtGui import QFont, QColor, QFontDatabase, QIcon, QShortcut, QKeySequence

from geoview_pyside6.constants import (
    Category, CATEGORY_THEMES, Light, Font, Space, Radius
)
from geoview_pyside6.theme_aware import c
from geoview_pyside6 import effects as _effects_mod
from geoview_pyside6.effects import PressEffect
from geoview_pyside6.i18n import LanguageManager
from geoview_pyside6.themes import apply_theme
from geoview_pyside6.widgets.animated_stack import AnimatedStackedWidget

_logger = logging.getLogger(__name__)


class SidebarButton(QPushButton):
    """사이드바 네비게이션 버튼 — QIcon(SVG) 또는 유니코드 텍스트 지원."""

    def __init__(self, icon_or_text, label: str, panel_id: str,
                 accent: str = "#10B981", parent=None):
        super().__init__(parent)
        self.panel_id = panel_id
        self.label_text = label
        self._active = False
        self._accent = accent
        self._icon_name: str | None = None  # SVG 아이콘 이름 (상태별 색상 전환용)
        self._collapsed_mode = False

        if isinstance(icon_or_text, QIcon) and not icon_or_text.isNull():
            # SVG QIcon 모드
            self.icon_text = ""
            self.setIcon(icon_or_text)
            self.setIconSize(QSize(18, 18))
            self.setText(f"  {label}")
        else:
            # 레거시 유니코드 텍스트 모드 (폴백)
            self.icon_text = icon_or_text if isinstance(icon_or_text, str) else ""
            if self.icon_text and self.icon_text.strip():
                self.setText(f"{self.icon_text}  {label}")
            else:
                self.setText(label)

        self.setFixedHeight(38)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setCheckable(True)
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self.setObjectName("sidebarButton")

        # Accessibility
        self.setAccessibleName(label)
        self.setAccessibleDescription(f"Navigate to {label}")

    def set_icon_name(self, name: str):
        """SVG 아이콘 이름 저장 (상태별 색상 전환에 사용)."""
        self._icon_name = name

    def set_active(self, active: bool):
        self._active = active
        self.setChecked(active)
        self._update_icon_color()
        if active and self._icon_name:
            self._bounce_icon()

    def _bounce_icon(self):
        """아이콘 활성화 시 약간의 바운스."""
        from geoview_pyside6.effects import anim_duration
        dur = anim_duration(200)
        if dur == 0:
            return

        original = self.iconSize()
        small = QSize(14, 14)

        # Shrink then expand (OutBack gives slight overshoot)
        self.setIconSize(small)

        from PySide6.QtCore import QPropertyAnimation, QEasingCurve
        self._bounce_anim = QPropertyAnimation(self, b"iconSize")
        self._bounce_anim.setDuration(dur)
        self._bounce_anim.setStartValue(small)
        self._bounce_anim.setEndValue(original)
        self._bounce_anim.setEasingCurve(QEasingCurve.Type.OutBack)
        self._bounce_anim.start()

    def _update_icon_color(self):
        """checked 상태에 따라 아이콘 색상 전환: accent(활성) / muted(비활성)."""
        if self._icon_name is None:
            return
        try:
            from geoview_pyside6.icons import icon as _icon
            if self._active:
                self.setIcon(_icon(self._icon_name, color=self._accent))
            else:
                self.setIcon(_icon(self._icon_name))  # 기본 muted 색상
        except Exception:
            pass  # 아이콘 로드 실패 시 무시

    def set_collapsed_mode(self, collapsed: bool):
        """접힌 모드: 아이콘만 표시, 라벨을 툴팁으로."""
        self._collapsed_mode = collapsed
        if collapsed:
            if self._icon_name:
                self.setText("")
            else:
                self.setText(self.icon_text if self.icon_text else self.label_text[:1])
            self.setToolTip(self.label_text)
            self.setFixedHeight(38)
            # Center icon: remove left border offset, symmetric padding
            self.setStyleSheet(
                "QPushButton {"
                "  border-left: none;"
                "  padding: 8px 0px;"
                "  margin: 1px 4px;"
                "  text-align: center;"
                "}"
            )
        else:
            if self._icon_name:
                self.setText(f"  {self.label_text}")
            elif self.icon_text and self.icon_text.strip():
                self.setText(f"{self.icon_text}  {self.label_text}")
            else:
                self.setText(self.label_text)
            self.setToolTip("")
            self.setStyleSheet("")  # Reset to theme QSS


class Sidebar(QFrame):
    """사이드바 네비게이션 — 브랜드 + 메뉴 + 하단 정보."""

    panel_changed = Signal(str)
    collapsed_changed = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setMinimumWidth(160)
        self.setMaximumWidth(300)
        self.buttons: list[SidebarButton] = []
        self._accent = "#10B981"
        self._collapsed = False

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)
        self._separator_labels: list[QLabel] = []

        # Brand area
        self.brand_frame = QFrame()
        self.brand_frame.setObjectName("sidebarBrand")
        self.brand_frame.setFixedHeight(56)
        brand_layout = QVBoxLayout(self.brand_frame)
        brand_layout.setContentsMargins(18, 14, 18, 14)
        brand_layout.setSpacing(2)

        self.brand_label = QLabel()
        self.brand_label.setObjectName("brandLabel")

        self.version_label = QLabel()
        self.version_label.setObjectName("versionLabel")

        brand_layout.addWidget(self.brand_label)
        brand_layout.addWidget(self.version_label)

        self._layout.addWidget(self.brand_frame)

        # Collapse toggle button (between brand and nav)
        self._collapse_btn = QPushButton()
        self._collapse_btn.setObjectName("collapseButton")
        self._collapse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._collapse_btn.setFixedHeight(28)
        self._collapse_btn.clicked.connect(self.toggle_collapsed)
        self._collapse_btn.setToolTip("Collapse sidebar")
        self._layout.addWidget(self._collapse_btn)
        self._update_collapse_button()

        # Navigation label — uses #sidebarSectionLabel from theme QSS
        self.nav_header = QLabel("MENU")
        self.nav_header.setObjectName("sidebarSectionLabel")
        self._layout.addWidget(self.nav_header)

        # Navigation buttons
        self._nav_layout = QVBoxLayout()
        self._nav_layout.setSpacing(1)
        self._nav_layout.setContentsMargins(Space.SM, 0, Space.SM, 0)
        self._layout.addLayout(self._nav_layout)

        self._layout.addStretch()

        # Bottom info
        self._bottom_frame = QFrame()
        self._bottom_frame.setObjectName("sidebarFooter")
        bottom_layout = QVBoxLayout(self._bottom_frame)
        bottom_layout.setContentsMargins(18, Space.SM, 18, Space.SM)
        bottom_layout.setSpacing(2)

        self._status_dot = QLabel()
        self._status_dot.setObjectName("sidebarFooterText")
        self._status_dot.setText("Ready")
        bottom_layout.addWidget(self._status_dot)

        self._layout.addWidget(self._bottom_frame)

    def set_brand(self, name: str, version: str, accent: str):
        self._accent = accent
        self.brand_label.setText(name)
        self.version_label.setText(version)

    def add_button(self, icon_or_text, label: str, panel_id: str) -> SidebarButton:
        btn = SidebarButton(icon_or_text, label, panel_id, self._accent)
        # QIcon에 부착된 아이콘 이름을 SidebarButton에 전달 (상태별 색상 전환용)
        if isinstance(icon_or_text, QIcon):
            icon_name = getattr(icon_or_text, "_gv_icon_name", None)
            if icon_name:
                btn.set_icon_name(icon_name)
        btn.clicked.connect(lambda checked, pid=panel_id: self._on_click(pid))
        PressEffect.apply(btn)
        self._nav_layout.addWidget(btn)
        self.buttons.append(btn)
        return btn

    def add_separator(self, label: str = ""):
        if label:
            sep = QLabel(label.upper())
            sep.setObjectName("sidebarSectionLabel")
            self._nav_layout.addWidget(sep)
            self._separator_labels.append(sep)
        else:
            spacer = QWidget()
            spacer.setFixedHeight(Space.SM)
            spacer.setStyleSheet("background: transparent;")
            self._nav_layout.addWidget(spacer)

    def set_static_text(self, nav_header: str | None = None, status_text: str | None = None, separators: list[str] | None = None):
        if nav_header is not None:
            self.nav_header.setText(nav_header)
        if status_text is not None:
            self._status_dot.setText(status_text)
        if separators is not None:
            for label, text in zip(self._separator_labels, separators):
                label.setText(text)

    def _on_click(self, panel_id: str):
        for btn in self.buttons:
            btn.set_active(btn.panel_id == panel_id)
        self.panel_changed.emit(panel_id)

    def set_active_panel(self, panel_id: str):
        self._on_click(panel_id)

    # ── Collapse / Expand ──

    def toggle_collapsed(self):
        """접힌 상태 토글."""
        self.set_collapsed(not self._collapsed)

    def set_collapsed(self, collapsed: bool):
        """사이드바 접힘/펼침 설정."""
        self._collapsed = collapsed
        if collapsed:
            self.setMinimumWidth(48)
            self.setMaximumWidth(48)
            # Hide text elements
            self.brand_label.hide()
            self.version_label.hide()
            self.nav_header.hide()
            self._status_dot.hide()
            for label in self._separator_labels:
                label.hide()
            # Collapse buttons to icon-only
            for btn in self.buttons:
                btn.set_collapsed_mode(True)
        else:
            self.setMinimumWidth(160)
            self.setMaximumWidth(300)
            self.brand_label.show()
            self.version_label.show()
            self.nav_header.show()
            self._status_dot.show()
            for label in self._separator_labels:
                label.show()
            for btn in self.buttons:
                btn.set_collapsed_mode(False)

        self._update_collapse_button()
        self.collapsed_changed.emit(collapsed)

    def _update_collapse_button(self):
        """접힘 토글 버튼의 아이콘/텍스트를 현재 상태에 맞게 갱신."""
        try:
            from geoview_pyside6.icons import icon as _icon
            if self._collapsed:
                self._collapse_btn.setIcon(_icon("panel-left-open", "#7C8694"))
                self._collapse_btn.setText("")
                self._collapse_btn.setToolTip("Expand sidebar")
            else:
                self._collapse_btn.setIcon(_icon("panel-left-close", "#7C8694"))
                self._collapse_btn.setText("")
                self._collapse_btn.setToolTip("Collapse sidebar")
            self._collapse_btn.setIconSize(QSize(16, 16))
        except Exception:
            # Fallback to unicode chevrons if icons unavailable
            if self._collapsed:
                self._collapse_btn.setText("\u00BB")  # >>
                self._collapse_btn.setToolTip("Expand sidebar")
            else:
                self._collapse_btn.setText("\u00AB")  # <<
                self._collapse_btn.setToolTip("Collapse sidebar")


class TopBar(QFrame):
    """상단 바 — 타이틀 + 액션 버튼."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("topBar")
        self.setFixedHeight(48)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(Space.LG, 0, Space.LG, 0)

        self.title_label = QLabel()
        self.title_label.setObjectName("topBarTitle")
        self.title_label.setAccessibleName("Current panel title")
        layout.addWidget(self.title_label)

        layout.addStretch()

        self.actions_layout = QHBoxLayout()
        self.actions_layout.setSpacing(Space.SM)
        layout.addLayout(self.actions_layout)

    def set_title(self, text: str):
        self.title_label.setText(text)
        self.title_label.setAccessibleName(text)

    def add_action_button(self, text: str, callback, primary=False) -> QPushButton:
        btn = QPushButton(text)
        btn.setObjectName("primaryButton" if primary else "secondaryButton")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(callback)
        # Subtle click sound feedback
        self.actions_layout.addWidget(btn)
        return btn


class GeoViewApp(QMainWindow):
    """
    GeoView 프로그램 공통 베이스 클래스.
    상속하여 APP_NAME, APP_VERSION, CATEGORY를 설정하고 setup_panels()를 구현.
    """

    APP_NAME: str = "GeoView"
    APP_VERSION: str = "v1.0.0"
    CATEGORY: Category = Category.PROCESSING
    USE_PROJECT_CONTEXT: bool = True  # False로 설정하면 컨텍스트 비활성

    def __init__(self):
        super().__init__()
        self._panels: dict[str, QWidget] = {}
        self._panel_order: list[str] = []
        self._current_panel: Optional[str] = None
        self._dirty: bool = False
        self._docks: dict[str, QDockWidget] = {}
        self._panel_history: list[str] = []
        self._history_index: int = -1

        # Project context (opt-in, 실패해도 앱 시작에 영향 없음)
        self.project_context = None  # Optional[ProjectContext]
        self._context_watcher = None
        self._project_label: Optional[QLabel] = None

        theme = CATEGORY_THEMES[self.CATEGORY]

        # Window setup
        self.setWindowTitle(f"{self.APP_NAME} {self.APP_VERSION}")

        # Set app window icon
        try:
            from geoview_pyside6.icons.app_icons import set_app_icon
            set_app_icon(self.CATEGORY)
        except Exception:
            pass
        self.setMinimumSize(1280, 800)
        self.resize(1440, 900)

        # -- Restore window geometry --
        self._settings = QSettings("GeoView", self.APP_NAME, self)
        if self._settings.contains("geometry"):
            self.restoreGeometry(self._settings.value("geometry"))
        # Note: windowState/dock_state restored AFTER setup_panels() to include dock widgets

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Sidebar
        self.sidebar = Sidebar()
        self.sidebar.set_brand(self.APP_NAME, self.APP_VERSION, theme.accent)
        self.sidebar.panel_changed.connect(self._switch_panel)

        # Right area (topbar + content)
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        self.top_bar = TopBar()
        right_layout.addWidget(self.top_bar)

        from geoview_pyside6.widgets.breadcrumb import BreadcrumbBar
        self._breadcrumb_bar = BreadcrumbBar()
        self._breadcrumb_bar.crumb_clicked.connect(self._on_breadcrumb_clicked)
        right_layout.addWidget(self._breadcrumb_bar)

        self.content_stack = AnimatedStackedWidget(duration=200)
        self.content_stack.setObjectName("contentStack")
        right_layout.addWidget(self.content_stack)

        # QSplitter: resizable sidebar
        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._splitter.setChildrenCollapsible(False)
        self._splitter.addWidget(self.sidebar)
        self._splitter.addWidget(right)

        saved_sidebar_w = self._settings.value("sidebar_width", 200, type=int)
        self._splitter.setSizes([saved_sidebar_w, 1440 - saved_sidebar_w])
        self._splitter.setHandleWidth(1)

        main_layout.addWidget(self._splitter)

        # Connect sidebar collapse to splitter resize
        self.sidebar.collapsed_changed.connect(self._on_sidebar_collapsed)

        # Restore sidebar collapsed state
        was_collapsed = self._settings.value("sidebar_collapsed", False, type=bool)
        if was_collapsed:
            self.sidebar.set_collapsed(True)
            self._splitter.setSizes([48, self.width() - 48])

        # Status bar
        self.status_bar = QStatusBar()
        self.status_bar.setObjectName("gvStatusBar")
        self.setStatusBar(self.status_bar)

        # Status bar inline progress
        self._setup_status_progress()

        # Language manager (optional, shared infra)
        self.lang_manager = LanguageManager(parent=self)
        self._lang_button: Optional[QToolButton] = None
        self._setup_language_controls()
        self.lang_manager.language_changed.connect(self._on_language_changed_internal)

        # Theme mode (persisted) — 3 modes: beige (default), light, dark
        self._current_theme_mode = self._settings.value("theme_mode", "beige", type=str)
        if self._current_theme_mode not in ("dark", "light", "beige"):
            self._current_theme_mode = "beige"
        from geoview_pyside6 import theme_aware
        theme_aware.set_mode(self._current_theme_mode)
        self._setup_theme_toggle()

        # Reduce motion preference (persisted)
        _reduce = self._settings.value("reduce_motion", False, type=bool)
        _effects_mod.set_reduce_motion(_reduce)

        # Sound preference (persisted)
        try:
            from geoview_pyside6 import sounds as _sounds_mod
            _sound_on = self._settings.value("sound_enabled", True, type=bool)
            _sounds_mod.set_enabled(_sound_on)
        except Exception:
            pass

        # Notification bell button
        self._setup_bell_button()

        # Apply theme
        apply_theme(self, self._current_theme_mode, self.CATEGORY)

        # Initialize project context (safe — never crashes)
        if self.USE_PROJECT_CONTEXT:
            self._init_project_context()

        # Let subclass add panels
        self.setup_panels()

        # Activate first panel, then restore last active panel if saved
        if self._panel_order:
            self.sidebar.set_active_panel(self._panel_order[0])
        last_panel = self._settings.value("last_panel", "")
        if last_panel and last_panel in self._panels:
            self.sidebar.set_active_panel(last_panel)

        # Restore window/dock state (after panels registered)
        _ds = self._settings.value("dock_state")
        if _ds:
            self.restoreState(_ds)
        elif self._settings.contains("windowState"):
            self.restoreState(self._settings.value("windowState"))

        # Command palette + keyboard shortcuts
        self._setup_shortcuts()
        self._setup_command_palette()

        # System monitor (memory usage in status bar)
        self._setup_sys_monitor()

        # Welcome dialog (first run)
        self._check_welcome()

        # Dark titlebar (Windows 10/11)
        self._apply_dark_titlebar()

    def setup_panels(self):
        """서브클래스에서 오버라이드. add_panel()을 호출하여 패널 등록."""
        pass

    def add_panel(self, panel_id: str, icon_or_text, label: str, widget: QWidget):
        """사이드바 버튼 + 콘텐츠 패널 등록. icon_or_text: QIcon 또는 유니코드 str."""
        self._panels[panel_id] = widget
        self._panel_order.append(panel_id)
        self.content_stack.addWidget(widget)
        self.sidebar.add_button(icon_or_text, label, panel_id)

    def add_sidebar_separator(self, label: str = ""):
        self.sidebar.add_separator(label)

    # ── Dock panels (opt-in auxiliary panels) ──

    def add_dock_panel(
        self,
        dock_id: str,
        title: str,
        widget: QWidget,
        area=Qt.DockWidgetArea.RightDockWidgetArea,
        allowed_areas=Qt.DockWidgetArea.AllDockWidgetAreas,
    ) -> QDockWidget:
        """보조 도킹 패널 등록. 메인 패널(sidebar 전환)과 독립적으로 동작.

        도킹 패널은 드래그로 위치 변경, floating 분리, 탭 결합 가능.
        레이아웃은 앱 종료 시 자동 저장되고 재시작 시 복원됨.
        """
        dock = QDockWidget(title, self)
        dock.setObjectName(f"dock_{dock_id}")
        dock.setWidget(widget)
        dock.setAllowedAreas(allowed_areas)
        self.addDockWidget(area, dock)
        self._docks[dock_id] = dock
        return dock

    def tabify_docks(self, dock_id_a: str, dock_id_b: str):
        """두 도킹 패널을 같은 영역에 탭으로 묶기."""
        a = self._docks.get(dock_id_a)
        b = self._docks.get(dock_id_b)
        if a and b:
            self.tabifyDockWidget(a, b)
            a.raise_()

    # ── Language / i18n ──

    def _setup_language_controls(self) -> None:
        """Add a compact KO/EN switch to the status bar.

        Apps without any registered translations can still keep this control;
        it remains a no-op except for changing the current language state.
        """
        self._lang_button = QToolButton(self)
        self._lang_button.setObjectName("languageButton")
        self._lang_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._lang_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self._lang_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self._lang_button.setAccessibleName("Language toggle")

        lang_menu = QMenu(self._lang_button)
        action_ko = lang_menu.addAction("한국어")
        action_en = lang_menu.addAction("English")
        action_ko.triggered.connect(lambda: self.set_language("ko"))
        action_en.triggered.connect(lambda: self.set_language("en"))
        self._lang_button.setMenu(lang_menu)
        self._lang_button.clicked.connect(self.toggle_language)

        self.status_bar.addPermanentWidget(self._lang_button)
        self._update_language_button()

    def _update_language_button(self) -> None:
        if not self._lang_button:
            return
        current = "EN" if self.lang_manager.lang == "en" else "KO"
        self._lang_button.setText(current)
        self._lang_button.setToolTip(
            "Switch language / 언어 전환"
            if self.lang_manager.lang == "ko"
            else "언어 전환 / Switch language"
        )

    def _on_language_changed_internal(self, _lang: str) -> None:
        self._refresh_language_ui()

    def _refresh_language_ui(self, force: bool = False) -> None:
        """Refresh language-dependent UI and notify subclasses."""
        self._update_language_button()
        try:
            self.on_language_changed(self.lang_manager.lang, force=force)
        except TypeError:
            # Backward compatibility if a subclass overrides with the old signature.
            try:
                self.on_language_changed(self.lang_manager.lang)
            except Exception as exc:
                _logger.warning("[%s] on_language_changed 오류: %s", self.APP_NAME, exc)
        except Exception as exc:
            _logger.warning("[%s] on_language_changed 오류: %s", self.APP_NAME, exc)

    def register_translations(self, translations: dict[str, dict[str, str]] | None, refresh: bool = True) -> bool:
        """Register app-level translations and optionally refresh the active language.

        Apps can call this from setup_panels() after creating labels/widgets.
        """
        changed = self.lang_manager.register(translations)
        if refresh:
            self._refresh_language_ui(force=True)
        return changed

    def set_language(self, lang: str, refresh: bool = True) -> bool:
        """Set the active app language."""
        changed = self.lang_manager.set_lang(lang)
        if refresh and not changed:
            self._refresh_language_ui(force=True)
        return changed

    def toggle_language(self) -> bool:
        """Toggle between Korean and English."""
        return self.set_language("en" if self.lang_manager.lang == "ko" else "ko")

    def t(self, key: str, default: Optional[str] = None) -> str:
        """Translate a key using the app-local language registry."""
        return self.lang_manager.t(key, default)

    def on_language_changed(self, lang: str, force: bool = False) -> None:
        """Subclass hook called after the app language changes or refreshes.

        Default implementation does nothing. Subclasses can update panel
        titles, helper text, labels, etc.
        """
        return

    # ── Theme Toggle ──

    def _setup_theme_toggle(self):
        """상태바에 다크/라이트 모드 토글 버튼 추가."""
        from geoview_pyside6.icons import icon as _icon

        self._theme_btn = QToolButton(self)
        self._theme_btn.setObjectName("themeToggle")
        self._theme_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._theme_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self._theme_btn.setFixedSize(28, 28)
        self._theme_btn.setAccessibleName("Theme toggle")
        self._theme_btn.clicked.connect(self._toggle_theme)
        self.status_bar.insertPermanentWidget(0, self._theme_btn)
        self._update_theme_button()

    # Theme cycle order: beige → skyblue → light → dark → beige
    _THEME_CYCLE = ["beige", "skyblue", "light", "dark"]

    _THEME_LABELS = {
        "beige":   ("Warm Beige", "sun"),
        "skyblue": ("Sky Blue", "compass"),
        "light":   ("Clean Light", "eye"),
        "dark":    ("Neutral Dark", "moon"),
    }

    def _update_theme_button(self):
        """현재 테마에 맞게 토글 버튼 아이콘/텍스트/툴팁 갱신."""
        from geoview_pyside6.icons import icon as _icon
        from geoview_pyside6.theme_aware import c
        label, icon_name = self._THEME_LABELS.get(
            self._current_theme_mode, ("Warm Beige", "sun")
        )
        idx = self._THEME_CYCLE.index(self._current_theme_mode) if self._current_theme_mode in self._THEME_CYCLE else 0
        next_label = self._THEME_LABELS[self._THEME_CYCLE[(idx + 1) % len(self._THEME_CYCLE)]][0]

        t = c()
        self._theme_btn.setIcon(_icon(icon_name, t.MUTED))
        self._theme_btn.setToolTip(f"{label} -> {next_label}")
        self._theme_btn.setIconSize(QSize(16, 16))
        # 테마에 맞는 호버 색상 적용
        hover_bg = "rgba(255,255,255,0.08)" if self._current_theme_mode == "dark" else "rgba(0,0,0,0.06)"
        self._theme_btn.setStyleSheet(f"""
            QToolButton {{
                background: transparent;
                border: 1px solid {t.BORDER};
                border-radius: 6px;
                padding: 4px;
            }}
            QToolButton:hover {{
                background: {hover_bg};
                border-color: {t.BORDER_H};
            }}
        """)

    def _toggle_theme(self):
        """4-mode 테마 순환: beige → skyblue → light → dark → beige.
        테마 전환 후 모든 패널의 인라인 스타일을 재적용."""
        idx = self._THEME_CYCLE.index(self._current_theme_mode) if self._current_theme_mode in self._THEME_CYCLE else -1
        self._current_theme_mode = self._THEME_CYCLE[(idx + 1) % len(self._THEME_CYCLE)]
        self._settings.setValue("theme_mode", self._current_theme_mode)
        from geoview_pyside6 import theme_aware
        theme_aware.set_mode(self._current_theme_mode)
        apply_theme(self, self._current_theme_mode, self.CATEGORY)
        self._update_theme_button()
        self._update_icon_defaults()
        self._apply_dark_titlebar()
        # 인라인 스타일을 가진 모든 패널/위젯에 테마 재적용
        self._refresh_all_panel_styles()

    def _refresh_all_panel_styles(self):
        """테마 전환 시 모든 패널의 인라인 스타일을 c()의 새 값으로 재적용.
        각 패널이 on_theme_changed()를 구현하면 호출됨."""
        for i in range(self.content_stack.count()):
            panel = self.content_stack.widget(i)
            if hasattr(panel, 'on_theme_changed'):
                try:
                    panel.on_theme_changed()
                except Exception:
                    pass
        # Dock 위젯 테마 갱신
        for dock_id, dock in self._docks.items():
            widget = dock.widget() if dock else None
            if widget and hasattr(widget, 'refresh_theme'):
                try:
                    widget.refresh_theme()
                except Exception:
                    pass
        # Notification center 테마 갱신
        if hasattr(self, '_notification_center') and self._notification_center:
            try:
                self._notification_center.refresh_theme()
            except Exception:
                pass
        # 브레드크럼 바 테마 갱신
        if hasattr(self, '_breadcrumb_bar') and self._breadcrumb_bar:
            try:
                self._breadcrumb_bar.refresh_theme()
            except Exception:
                pass
        # 사이드바 브랜드 색상 업데이트
        theme = CATEGORY_THEMES.get(self.CATEGORY, CATEGORY_THEMES[Category.PROCESSING])
        self.sidebar.set_brand(self.APP_NAME, self.APP_VERSION, theme.accent)

    def _update_icon_defaults(self):
        """아이콘 기본 색상을 현재 테마에 맞게 갱신."""
        # icon_engine now uses c() dynamically, so just re-render sidebar icons
        try:
            for btn in self.sidebar.buttons:
                btn._update_icon_color()
        except Exception:
            pass  # 아이콘 갱신 실패 시 무시

    def _apply_dark_titlebar(self):
        """Windows 10/11에서 네이티브 타이틀바를 다크 모드로 전환."""
        if sys.platform != "win32":
            return
        try:
            import ctypes
            hwnd = int(self.winId())
            DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            value = ctypes.c_int(1 if self._current_theme_mode == "dark" else 0)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE,
                ctypes.byref(value), ctypes.sizeof(value),
            )
        except Exception:
            pass

    def _on_sidebar_collapsed(self, collapsed: bool):
        """Resize splitter when sidebar collapses/expands."""
        total = self._splitter.width()
        if collapsed:
            self._splitter.setSizes([48, total - 48])
        else:
            saved_w = self._settings.value("sidebar_width", 200, type=int)
            saved_w = max(160, min(300, saved_w))
            self._splitter.setSizes([saved_w, total - saved_w])

    def closeEvent(self, event):
        """Save window geometry and sidebar width on close."""
        if self._dirty:
            if not self.show_confirm("Unsaved Changes",
                    "You have unsaved changes. Close anyway?",
                    confirm_text="Close"):
                event.ignore()
                return
        self._settings.setValue("geometry", self.saveGeometry())
        self._settings.setValue("dock_state", self.saveState())
        self._settings.setValue("sidebar_width", self.sidebar.width())
        self._settings.setValue("sidebar_collapsed", self.sidebar._collapsed)
        super().closeEvent(event)

    # ── Dirty State ──

    def set_dirty(self, dirty: bool = True):
        """폼 데이터 변경 상태 설정. 타이틀에 * 표시."""
        self._dirty = dirty
        base_title = f"{self.APP_NAME} {self.APP_VERSION}"
        self.setWindowTitle(f"{base_title} *" if dirty else base_title)

    def is_dirty(self) -> bool:
        return self._dirty

    # ── Status Progress ──

    def _setup_status_progress(self):
        """상태바에 인라인 프로그레스 바 추가 (숨김 기본)."""
        from PySide6.QtWidgets import QProgressBar
        self._status_progress = QProgressBar(self)
        self._status_progress.setFixedWidth(120)
        self._status_progress.setFixedHeight(12)
        self._status_progress.setTextVisible(False)
        self._status_progress.setRange(0, 100)
        self._status_progress.hide()
        self.status_bar.insertPermanentWidget(0, self._status_progress)

    def show_status_progress(self, percent: int = -1, message: str = ""):
        """상태바 프로그레스 표시. percent=-1이면 indeterminate."""
        if percent < 0:
            self._status_progress.setRange(0, 0)  # indeterminate
        else:
            self._status_progress.setRange(0, 100)
            self._status_progress.setValue(min(100, max(0, percent)))
        self._status_progress.show()
        if message:
            self.status_bar.showMessage(message, 5000)

    def hide_status_progress(self):
        """상태바 프로그레스 숨김."""
        self._status_progress.setRange(0, 100)
        self._status_progress.setValue(0)
        self._status_progress.hide()

    def show_toast(self, message: str, toast_type: str = "info",
                   duration: int = 3000):
        """Show a toast notification at bottom-right."""
        from geoview_pyside6.widgets.toast import Toast
        toast = Toast(message, toast_type, duration, parent=self)
        toast.setParent(self)
        toast.raise_()
        # Position bottom-right
        margin = Space.LG
        x = self.width() - toast.sizeHint().width() - margin
        y = self.height() - toast.sizeHint().height() - margin - 30  # above status bar
        toast.move(x, y)
        toast.show()

        # Play notification sound
        try:
            from geoview_pyside6.sounds import play
            play("notify")
        except Exception:
            pass

        # Log to notification center
        self._ensure_notification_center()
        self._notification_center.log(message, toast_type)

    # ── Dialog Factory Methods ──

    def show_error(self, title: str, message: str) -> bool:
        """Show an error dialog (OK button only)."""
        from geoview_pyside6.widgets.confirm_dialog import ConfirmDialog
        dlg = ConfirmDialog(title, message, confirm_text="OK", cancel_text="",
                            dialog_type="error", parent=self)
        return dlg.exec() == dlg.Accepted

    def show_warning(self, title: str, message: str) -> bool:
        """Show a warning confirmation dialog (Continue / Cancel)."""
        from geoview_pyside6.widgets.confirm_dialog import ConfirmDialog
        dlg = ConfirmDialog(title, message, confirm_text="Continue", cancel_text="Cancel",
                            dialog_type="warning", parent=self)
        return dlg.exec() == dlg.Accepted

    def show_confirm(self, title: str, message: str, confirm_text: str = "Confirm") -> bool:
        """Show a general confirmation dialog (Confirm / Cancel)."""
        from geoview_pyside6.widgets.confirm_dialog import ConfirmDialog
        dlg = ConfirmDialog(title, message, confirm_text=confirm_text, cancel_text="Cancel",
                            dialog_type="info", parent=self)
        return dlg.exec() == dlg.Accepted

    # ── System Monitor ──

    def _setup_sys_monitor(self):
        """상태바에 메모리 사용량 표시."""
        self._mem_label = QLabel()
        self._mem_label.setStyleSheet(f"""
            font-size: {Font.XS}px;
            color: {c().DIM};
            padding: 0 {Space.SM}px;
            background: transparent;
        """)
        self.status_bar.addPermanentWidget(self._mem_label)

        from PySide6.QtCore import QTimer
        self._mem_timer = QTimer(self)
        self._mem_timer.timeout.connect(self._update_mem)
        self._mem_timer.start(5000)
        self._update_mem()

    def _update_mem(self):
        """메모리 사용량 갱신."""
        try:
            import psutil
            proc = psutil.Process()
            mem_mb = proc.memory_info().rss / (1024 * 1024)
            self._mem_label.setText(f"{mem_mb:.0f} MB")
        except ImportError:
            # psutil not available -- use less accurate method
            import os
            if hasattr(os, 'getpid'):
                try:
                    import resource
                    mem_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
                    self._mem_label.setText(f"{mem_kb // 1024} MB")
                except (ImportError, AttributeError):
                    self._mem_label.hide()
        except Exception:
            pass

    # ── Loading Overlay ──

    def show_loading(self, message: str = ""):
        """콘텐츠 영역에 로딩 오버레이 표시."""
        if not hasattr(self, '_loading_overlay') or self._loading_overlay is None:
            from geoview_pyside6.widgets.loading_spinner import LoadingOverlay
            self._loading_overlay = LoadingOverlay(parent=self.content_stack)
        self._loading_overlay.show_loading(message)

    def hide_loading(self):
        """로딩 오버레이 숨김."""
        if hasattr(self, '_loading_overlay') and self._loading_overlay:
            self._loading_overlay.hide_loading()

    def _switch_panel(self, panel_id: str, *, _from_history: bool = False):
        """패널 전환.

        Args:
            panel_id: 전환할 패널 ID.
            _from_history: True이면 히스토리 이동에 의한 전환 (히스토리 추가 건너뜀).
        """
        old_panel = self._current_panel
        self._current_panel = panel_id
        self._settings.setValue("last_panel", panel_id)
        panel = self._panels.get(panel_id)
        if panel:
            # 방향성 전환: 패널 순서 기반
            direction = "fade"
            if old_panel and old_panel != panel_id:
                try:
                    old_idx = self._panel_order.index(old_panel)
                    new_idx = self._panel_order.index(panel_id)
                    direction = "forward" if new_idx > old_idx else "back"
                except ValueError:
                    pass
            self.content_stack.set_current_with_animation(panel, direction=direction)
            title = getattr(panel, 'panel_title', panel_id.replace('_', ' ').title())
            self.top_bar.set_title(title)

            # 히스토리 관리
            if not _from_history:
                # 현재 위치 이후의 히스토리 잘라내기
                if self._history_index < len(self._panel_history) - 1:
                    self._panel_history = self._panel_history[:self._history_index + 1]
                self._panel_history.append(panel_id)
                self._history_index = len(self._panel_history) - 1

            # 브레드크럼 업데이트
            self._update_breadcrumb()

            if hasattr(panel, 'on_panel_activated'):
                panel.on_panel_activated()

    def get_panel(self, panel_id: str) -> Optional[QWidget]:
        return self._panels.get(panel_id)

    # ── Breadcrumb & History ──

    def _update_breadcrumb(self) -> None:
        """현재 히스토리를 기반으로 브레드크럼 업데이트."""
        if not self._panel_history:
            self._breadcrumb_bar.set_path([])
            return

        # 히스토리에서 현재 위치까지의 고유 경로 구성 (중복 제거, 순서 유지)
        seen: set[str] = set()
        path: list[tuple[str, str]] = []
        for pid in self._panel_history[:self._history_index + 1]:
            if pid not in seen:
                seen.add(pid)
                panel = self._panels.get(pid)
                label = getattr(panel, 'panel_title', pid.replace('_', ' ').title()) if panel else pid
                path.append((pid, label))

        # 브레드크럼 경로가 1개면 (현재 위치만) 숨김
        if len(path) <= 1:
            self._breadcrumb_bar.set_path([])
        else:
            self._breadcrumb_bar.set_path(path)

    def _on_breadcrumb_clicked(self, panel_id: str) -> None:
        """브레드크럼 항목 클릭 시 해당 패널로 이동."""
        if panel_id in self._panels:
            self.sidebar.set_active_panel(panel_id)

    def _history_back(self) -> None:
        """Alt+Left: 이전 패널로 이동."""
        if self._history_index > 0:
            self._history_index -= 1
            pid = self._panel_history[self._history_index]
            # 사이드바 버튼 상태 업데이트 (재귀 방지를 위해 직접 호출)
            for btn in self.sidebar.buttons:
                btn.set_active(btn.panel_id == pid)
            self._switch_panel(pid, _from_history=True)

    def _history_forward(self) -> None:
        """Alt+Right: 다음 패널로 이동."""
        if self._history_index < len(self._panel_history) - 1:
            self._history_index += 1
            pid = self._panel_history[self._history_index]
            for btn in self.sidebar.buttons:
                btn.set_active(btn.panel_id == pid)
            self._switch_panel(pid, _from_history=True)

    # ── Project Context ──

    def _init_project_context(self) -> None:
        """프로젝트 컨텍스트 초기화. 실패해도 앱 시작에 영향 없음."""
        try:
            from geoview_common.project_context import ProjectContextStore
            from geoview_common.project_context.signals import create_watcher

            self._context_store = ProjectContextStore()
            self.project_context = self._context_store.load_active()

            # 환경변수 폴백: LaunchPad가 GEOVIEW_PROJECT_FILE을 주입한 경우
            if self.project_context is None:
                import os
                env_file = os.environ.get("GEOVIEW_PROJECT_FILE")
                if env_file and Path(env_file).exists():
                    from geoview_common.project_context.models import ProjectContext as _PC
                    self.project_context = _PC.from_file(env_file)

            # Watcher 생성 및 시작
            self._context_watcher = create_watcher(
                active_file=self._context_store.active_file,
                store=self._context_store,
            )
            if self._context_watcher:
                self._context_watcher.setParent(self)
                self._context_watcher.context_changed.connect(self._on_context_changed_internal)
                self._context_watcher.start()

            # 상태바에 프로젝트명 표시
            self._setup_project_status_label()
            self._update_project_status_label()

            # 경로 유효성 경고
            if self.project_context:
                warnings = self.project_context.validate_paths()
                for w in warnings:
                    _logger.warning("[%s] 경로 없음: %s", self.APP_NAME, w)

        except ImportError:
            _logger.debug("geoview_common.project_context 미설치 — 컨텍스트 비활성")
        except Exception as e:
            _logger.warning("프로젝트 컨텍스트 초기화 실패: %s", e)

    def _setup_project_status_label(self) -> None:
        """상태바 우측에 현재 프로젝트명 라벨 추가."""
        self._project_label = QLabel()
        self._project_label.setStyleSheet(f"""
            font-size: {Font.XS}px;
            color: {c().DIM};
            padding: 0 {Space.SM}px;
            background: transparent;
        """)
        self.status_bar.addPermanentWidget(self._project_label)

    def _update_project_status_label(self) -> None:
        """프로젝트 라벨 텍스트 갱신."""
        if not self._project_label:
            return
        if self.project_context:
            name = self.project_context.display_name()
            self._project_label.setText(f"Project: {name}")
            self._project_label.setStyleSheet(f"""
                font-size: {Font.XS}px;
                color: {c().MUTED};
                padding: 0 {Space.SM}px;
                background: transparent;
            """)
        else:
            self._project_label.setText("No Active Project")

    def _on_context_changed_internal(self, ctx) -> None:
        """내부 컨텍스트 변경 핸들러."""
        old_ctx = self.project_context
        self.project_context = ctx
        self._update_project_status_label()

        # 경로 유효성 경고
        if ctx:
            warnings = ctx.validate_paths()
            for w in warnings:
                _logger.warning("[%s] 경로 없음: %s", self.APP_NAME, w)

        # 서브클래스 훅 호출
        try:
            self.on_project_context_changed(ctx, old_ctx)
        except Exception as e:
            _logger.warning("[%s] on_project_context_changed 오류: %s", self.APP_NAME, e)

    def on_project_context_changed(self, ctx, old_ctx=None) -> None:
        """
        서브클래스 오버라이드 포인트.

        프로젝트 컨텍스트가 변경될 때 호출됨.
        기본 구현은 아무것도 하지 않음.

        Parameters
        ----------
        ctx : ProjectContext or None
            새로운 프로젝트 컨텍스트. None이면 활성 프로젝트 해제.
        old_ctx : ProjectContext or None
            이전 프로젝트 컨텍스트.
        """
        pass

    # ── Help / Discoverability ──

    def _setup_shortcuts(self) -> None:
        """전역 키보드 단축키 등록."""
        QShortcut(QKeySequence("Ctrl+K"), self, self._show_command_palette)
        QShortcut(
            QKeySequence("Ctrl+H"), self,
            lambda: self.sidebar.set_active_panel(self._panel_order[0])
            if self._panel_order else None,
        )
        QShortcut(QKeySequence("Ctrl+L"), self, self.toggle_language)
        QShortcut(QKeySequence("Ctrl+Shift+T"), self, self._toggle_theme)
        QShortcut(QKeySequence("F11"), self, self._toggle_fullscreen)
        QShortcut(QKeySequence("Ctrl+,"), self, self._show_settings)
        QShortcut(QKeySequence("Ctrl+Shift+N"), self, self._toggle_notification_center)
        QShortcut(QKeySequence("Ctrl+B"), self, self.sidebar.toggle_collapsed)
        QShortcut(QKeySequence("Alt+Left"), self, self._history_back)
        QShortcut(QKeySequence("Alt+Right"), self, self._history_forward)

    def _setup_command_palette(self) -> None:
        """커맨드 팔레트 초기화 및 기본 액션 등록 (Ctrl+K)."""
        from geoview_pyside6.widgets.command_palette import CommandPalette

        # Overlay widget -- parented to centralWidget so it covers content area
        central = self.centralWidget()
        self._cmd_palette = CommandPalette(parent=central or self)

        # Auto-register all sidebar panels as Navigation actions
        for pid in self._panel_order:
            panel = self._panels[pid]
            label = getattr(panel, "panel_title", pid.replace("_", " ").title())
            self._cmd_palette.register_action(
                f"panel.{pid}", f"Go to {label}", category="Navigation",
                callback=lambda p=pid: self.sidebar.set_active_panel(p),
            )

        # Standard built-in actions
        self._cmd_palette.register_action(
            "home", "Go to Home",
            "Ctrl+H", "Navigation",
            callback=lambda: (
                self.sidebar.set_active_panel(self._panel_order[0])
                if self._panel_order else None
            ),
        )
        self._cmd_palette.register_action(
            "settings.open", "Open Settings",
            "Ctrl+,", "Settings",
            callback=self._show_settings,
        )
        self._cmd_palette.register_action(
            "theme.toggle", "Toggle Dark/Light Mode",
            "Ctrl+Shift+T", "Settings",
            callback=self._toggle_theme,
        )
        self._cmd_palette.register_action(
            "lang.toggle", "Toggle Language (KO/EN)",
            "Ctrl+L", "Settings",
            callback=self.toggle_language,
        )
        self._cmd_palette.register_action(
            "fullscreen", "Toggle Fullscreen",
            "F11", "View",
            callback=self._toggle_fullscreen,
        )
        self._cmd_palette.register_action(
            "notifications.toggle", "Toggle Notifications",
            "Ctrl+Shift+N", "View",
            callback=self._toggle_notification_center,
        )
        self._cmd_palette.register_action(
            "sidebar.toggle", "Toggle Sidebar",
            "Ctrl+B", "View",
            callback=self.sidebar.toggle_collapsed,
        )
        self._cmd_palette.register_action(
            "history.back", "Go Back",
            "Alt+Left", "Navigation",
            callback=self._history_back,
        )
        self._cmd_palette.register_action(
            "history.forward", "Go Forward",
            "Alt+Right", "Navigation",
            callback=self._history_forward,
        )

    def _show_command_palette(self) -> None:
        """커맨드 팔레트 표시 (Ctrl+K)."""
        if self._cmd_palette.isVisible():
            self._cmd_palette.hide_palette()
        else:
            self._cmd_palette.show_palette()

    def _toggle_fullscreen(self) -> None:
        """전체화면 토글."""
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    # ── Settings Panel ──

    def _show_settings(self) -> None:
        """설정 패널 표시."""
        from geoview_pyside6.widgets.settings_panel import SettingsPanel
        dlg = SettingsPanel(app_ref=self, parent=self)
        dlg.exec()

    # ── Notification Center ──

    def _ensure_notification_center(self) -> None:
        """알림 센터 lazy 초기화."""
        if not hasattr(self, '_notification_center') or self._notification_center is None:
            from geoview_pyside6.widgets.notification_center import NotificationCenter
            self._notification_center = NotificationCenter(parent=self.centralWidget())
            self._notification_center.hide()
            self._notification_center.unread_changed.connect(self._update_bell_badge)

    def _toggle_notification_center(self) -> None:
        """알림 센터 토글."""
        self._ensure_notification_center()
        self._notification_center.toggle()

    def _setup_bell_button(self) -> None:
        """상태바에 알림 벨 버튼 추가."""
        from geoview_pyside6.icons import icon as _icon

        self._bell_btn = QToolButton(self)
        self._bell_btn.setObjectName("bellButton")
        self._bell_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._bell_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self._bell_btn.setFixedSize(28, 28)
        self._bell_btn.setIcon(_icon("bell", "#7C8694"))
        self._bell_btn.setIconSize(QSize(16, 16))
        self._bell_btn.setToolTip("Notifications (Ctrl+Shift+N)")
        self._bell_btn.clicked.connect(self._toggle_notification_center)
        self._bell_btn.setStyleSheet("""
            QToolButton {
                background: transparent;
                border: none;
                border-radius: 4px;
                padding: 4px;
            }
            QToolButton:hover {
                background: rgba(255,255,255,0.08);
            }
        """)

        # Badge (overlaid on bell button)
        self._bell_badge = QLabel("0", self._bell_btn)
        self._bell_badge.setFixedSize(16, 14)
        self._bell_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._bell_badge.setStyleSheet(f"""
            font-size: 9px;
            font-weight: 700;
            color: {c().BG};
            background: {c().CYAN};
            border-radius: 7px;
            padding: 0;
        """)
        self._bell_badge.move(15, 0)
        self._bell_badge.hide()

        self.status_bar.insertPermanentWidget(0, self._bell_btn)

    def _update_bell_badge(self, count: int) -> None:
        """벨 버튼 배지 업데이트."""
        if not hasattr(self, '_bell_badge'):
            return
        if count > 0:
            text = str(count) if count < 100 else "99+"
            self._bell_badge.setText(text)
            self._bell_badge.show()
        else:
            self._bell_badge.hide()

    def _check_welcome(self) -> None:
        """첫 실행 시 환영 다이얼로그 예약."""
        key = f"welcome/{self.APP_NAME}/shown"
        if not self._settings.value(key, False, type=bool):
            from PySide6.QtCore import QTimer
            QTimer.singleShot(500, self._show_welcome)

    def _show_welcome(self) -> None:
        """환영 다이얼로그 표시 (WELCOME_FEATURES가 정의된 경우에만)."""
        features = getattr(self, 'WELCOME_FEATURES', None)
        if not features:
            return
        from geoview_pyside6.widgets.welcome_dialog import WelcomeDialog
        dlg = WelcomeDialog(
            self.APP_NAME, self.APP_VERSION, features, parent=self,
        )
        dlg.exec()
        if dlg.dont_show_again:
            self._settings.setValue(f"welcome/{self.APP_NAME}/shown", True)

    @classmethod
    def run(cls):
        """앱 실행 헬퍼."""
        app = QApplication(sys.argv)

        # Load fonts
        for font_file in (Path(__file__).parent / "fonts").rglob("*.[ot]tf"):
            QFontDatabase.addApplicationFont(str(font_file))

        # Set global default font — Wanted Sans Std: modern Korean UI font
        default_font = QFont("Wanted Sans Std", 11)  # 11pt
        default_font.setHintingPreference(QFont.HintingPreference.PreferFullHinting)
        app.setFont(default_font)

        # Show splash screen
        splash = None
        try:
            from geoview_pyside6.splash import GeoViewSplash
            splash = GeoViewSplash(cls.APP_NAME, cls.APP_VERSION, cls.CATEGORY)
            splash.show()
            splash.set_status("Initializing...")
            app.processEvents()
        except Exception:
            pass

        window = cls()

        if splash:
            splash.set_status("Ready")
            splash.finish_with_delay(window, 600)

        window.show()
        sys.exit(app.exec())
