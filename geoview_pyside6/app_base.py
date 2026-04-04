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
    QStatusBar, QToolButton, QMenu,
)
from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QFont, QColor, QFontDatabase

from geoview_pyside6.constants import (
    Category, CATEGORY_THEMES, Dark, Light, Font, Space, Radius
)
from geoview_pyside6.i18n import LanguageManager
from geoview_pyside6.themes import apply_theme

_logger = logging.getLogger(__name__)


class SidebarButton(QPushButton):
    """사이드바 네비게이션 버튼 — 좌측 인디케이터 바 포함."""

    def __init__(self, icon_text: str, label: str, panel_id: str,
                 accent: str = "#10B981", parent=None):
        super().__init__(parent)
        self.panel_id = panel_id
        self.icon_text = icon_text
        self.label_text = label
        self._active = False
        self._accent = accent

        self.setText(label)
        self.setFixedHeight(38)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setCheckable(True)
        self.setObjectName("sidebarButton")

    def set_active(self, active: bool):
        self._active = active
        self.setChecked(active)


class Sidebar(QFrame):
    """사이드바 네비게이션 — 브랜드 + 메뉴 + 하단 정보."""

    panel_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(200)
        self.buttons: list[SidebarButton] = []
        self._accent = "#10B981"

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)
        self._separator_labels: list[QLabel] = []

        # Brand area
        self.brand_frame = QFrame()
        self.brand_frame.setObjectName("sidebarBrand")
        self.brand_frame.setFixedHeight(56)
        brand_layout = QVBoxLayout(self.brand_frame)
        brand_layout.setContentsMargins(Space.LG, Space.SM, Space.LG, Space.SM)
        brand_layout.setSpacing(0)

        self.brand_label = QLabel()
        self.brand_label.setObjectName("brandLabel")

        self.version_label = QLabel()
        self.version_label.setObjectName("versionLabel")

        brand_layout.addWidget(self.brand_label)
        brand_layout.addWidget(self.version_label)

        self._layout.addWidget(self.brand_frame)

        # Navigation label
        self.nav_header = QLabel("MENU")
        self.nav_header.setStyleSheet(f"""
            font-size: 10px;
            font-weight: {Font.MEDIUM};
            color: {Dark.DIM};
            letter-spacing: 1.5px;
            padding: {Space.BASE}px {Space.LG}px {Space.XS}px;
            background: transparent;
        """)
        self._layout.addWidget(self.nav_header)

        # Navigation buttons
        self._nav_layout = QVBoxLayout()
        self._nav_layout.setSpacing(1)
        self._nav_layout.setContentsMargins(Space.SM, 0, Space.SM, 0)
        self._layout.addLayout(self._nav_layout)

        self._layout.addStretch()

        # Bottom info
        self._bottom_frame = QFrame()
        self._bottom_frame.setStyleSheet(f"""
            QFrame {{
                border-top: 1px solid {Dark.BORDER};
                background: transparent;
            }}
        """)
        bottom_layout = QVBoxLayout(self._bottom_frame)
        bottom_layout.setContentsMargins(Space.LG, Space.SM, Space.LG, Space.SM)
        bottom_layout.setSpacing(2)

        self._status_dot = QLabel()
        self._status_dot.setStyleSheet(f"""
            font-size: {Font.XS}px;
            color: {Dark.DIM};
            background: transparent;
        """)
        self._status_dot.setText("Ready")
        bottom_layout.addWidget(self._status_dot)

        self._layout.addWidget(self._bottom_frame)

    def set_brand(self, name: str, version: str, accent: str):
        self._accent = accent
        self.brand_label.setText(name)
        self.version_label.setText(version)

    def add_button(self, icon: str, label: str, panel_id: str) -> SidebarButton:
        btn = SidebarButton(icon, label, panel_id, self._accent)
        btn.clicked.connect(lambda checked, pid=panel_id: self._on_click(pid))
        self._nav_layout.addWidget(btn)
        self.buttons.append(btn)
        return btn

    def add_separator(self, label: str = ""):
        if label:
            sep = QLabel(label.upper())
            sep.setStyleSheet(f"""
                font-size: 10px;
                font-weight: {Font.MEDIUM};
                color: {Dark.DIM};
                letter-spacing: 1.5px;
                padding: {Space.MD}px {Space.SM}px {Space.XS}px;
                background: transparent;
            """)
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
        layout.addWidget(self.title_label)

        layout.addStretch()

        self.actions_layout = QHBoxLayout()
        self.actions_layout.setSpacing(Space.SM)
        layout.addLayout(self.actions_layout)

    def set_title(self, text: str):
        self.title_label.setText(text)

    def add_action_button(self, text: str, callback, primary=False) -> QPushButton:
        btn = QPushButton(text)
        btn.setObjectName("primaryButton" if primary else "secondaryButton")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(callback)
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

        # Project context (opt-in, 실패해도 앱 시작에 영향 없음)
        self.project_context = None  # Optional[ProjectContext]
        self._context_watcher = None
        self._project_label: Optional[QLabel] = None

        theme = CATEGORY_THEMES[self.CATEGORY]

        # Window setup
        self.setWindowTitle(f"{self.APP_NAME} {self.APP_VERSION}")
        self.setMinimumSize(1280, 800)
        self.resize(1440, 900)

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
        main_layout.addWidget(self.sidebar)

        # Right area (topbar + content)
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        self.top_bar = TopBar()
        right_layout.addWidget(self.top_bar)

        self.content_stack = QStackedWidget()
        self.content_stack.setObjectName("contentStack")
        right_layout.addWidget(self.content_stack)

        main_layout.addWidget(right)

        # Status bar
        self.status_bar = QStatusBar()
        self.status_bar.setObjectName("gvStatusBar")
        self.setStatusBar(self.status_bar)

        # Language manager (optional, shared infra)
        self.lang_manager = LanguageManager(parent=self)
        self._lang_button: Optional[QToolButton] = None
        self._setup_language_controls()
        self.lang_manager.language_changed.connect(self._on_language_changed_internal)

        # Apply theme
        apply_theme(self, "dark", self.CATEGORY)

        # Initialize project context (safe — never crashes)
        if self.USE_PROJECT_CONTEXT:
            self._init_project_context()

        # Let subclass add panels
        self.setup_panels()

        # Activate first panel
        if self._panel_order:
            self.sidebar.set_active_panel(self._panel_order[0])

    def setup_panels(self):
        """서브클래스에서 오버라이드. add_panel()을 호출하여 패널 등록."""
        pass

    def add_panel(self, panel_id: str, icon: str, label: str, widget: QWidget):
        """사이드바 버튼 + 콘텐츠 패널 등록."""
        self._panels[panel_id] = widget
        self._panel_order.append(panel_id)
        self.content_stack.addWidget(widget)
        self.sidebar.add_button(icon, label, panel_id)

    def add_sidebar_separator(self, label: str = ""):
        self.sidebar.add_separator(label)

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

    def _switch_panel(self, panel_id: str):
        """패널 전환."""
        self._current_panel = panel_id
        panel = self._panels.get(panel_id)
        if panel:
            self.content_stack.setCurrentWidget(panel)
            title = getattr(panel, 'panel_title', panel_id.replace('_', ' ').title())
            self.top_bar.set_title(title)

    def get_panel(self, panel_id: str) -> Optional[QWidget]:
        return self._panels.get(panel_id)

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
            color: {Dark.DIM};
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
                color: {Dark.MUTED};
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

    @classmethod
    def run(cls):
        """앱 실행 헬퍼."""
        app = QApplication(sys.argv)

        # Load fonts
        for font_file in (Path(__file__).parent / "fonts").glob("*.ttf"):
            QFontDatabase.addApplicationFont(str(font_file))

        # Set global default font
        db = QFontDatabase()
        if "Pretendard" in db.families():
            default_font = QFont("Pretendard", Font.BASE)
        elif "Noto Sans KR" in db.families():
            default_font = QFont("Noto Sans KR", Font.BASE)
        else:
            default_font = QFont("Segoe UI", Font.BASE)
        app.setFont(default_font)

        window = cls()
        window.show()
        sys.exit(app.exec())
