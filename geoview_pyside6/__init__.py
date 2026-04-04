"""
GeoView PySide6 Common Library
==============================
24개 프로그램이 공유하는 PySide6 기반 컴포넌트, 테마, 위젯 라이브러리.

Usage:
    from geoview_pyside6 import GeoViewApp, Category
    from geoview_pyside6.widgets import KPICard, DataTable, StatusBadge
    from geoview_pyside6.themes import apply_theme

Architecture:
    GeoViewApp (QMainWindow 기반)
      ├── Sidebar (카테고리 아이콘 + 패널 전환)
      ├── TopBar (앱 이름 + 검색 + 액션 버튼)
      ├── ContentStack (QStackedWidget — 패널 전환)
      └── StatusBar (포트/상태/단축키 힌트)
"""

__version__ = "1.0.0"

from geoview_pyside6.app_base import GeoViewApp, Category
from geoview_pyside6.i18n import (
    LanguageManager,
    get_language_manager,
    lang,
    on_lang_change,
    register_translations,
    set_lang,
    t,
    toggle_lang,
)

__all__ = [
    "GeoViewApp",
    "Category",
    "LanguageManager",
    "get_language_manager",
    "lang",
    "on_lang_change",
    "register_translations",
    "set_lang",
    "t",
    "toggle_lang",
]
