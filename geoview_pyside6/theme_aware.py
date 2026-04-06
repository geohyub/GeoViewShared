"""
GeoView PySide6 -- Theme-Aware Color Accessor
===============================================
위젯이 현재 테마 모드에 맞는 색상을 동적으로 얻는 모듈.

Usage::

    from geoview_pyside6.theme_aware import c

    self.setStyleSheet(f"background: {c().NAVY}; color: {c().TEXT};")

c() 는 호출 시점의 현재 테마 모드에 맞는 색상 클래스를 반환.
3 modes: 'dark' (Ocean Teal), 'light' (Clean Light), 'beige' (Warm Beige)
"""

_current_mode: str = "beige"


def set_mode(mode: str):
    """테마 모드 설정 (app_base.py에서 호출)."""
    global _current_mode
    _current_mode = mode


def mode() -> str:
    """현재 테마 모드 반환."""
    return _current_mode


def is_dark() -> bool:
    """현재 모드가 다크 계열인지 반환."""
    return _current_mode == "dark"


def c():
    """현재 모드의 색상 클래스 반환."""
    from geoview_pyside6.constants import Dark, Light, WarmBeige, SkyBlue
    _map = {"dark": Dark, "light": Light, "beige": WarmBeige, "skyblue": SkyBlue}
    return _map.get(_current_mode, WarmBeige)
