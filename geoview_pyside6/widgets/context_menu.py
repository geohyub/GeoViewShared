"""
Context Menu Factory
======================
프리스타일드 컨텍스트 메뉴 생성 팩토리.
3+ 앱에서 반복되는 컨텍스트 메뉴 패턴을 단일 함수로 통합.
"""

from __future__ import annotations

from typing import Callable

from PySide6.QtWidgets import QWidget, QMenu
from PySide6.QtGui import QAction

from geoview_pyside6.constants import Font, Radius
from geoview_pyside6.theme_aware import c


def create_context_menu(
    parent: QWidget,
    items: list,
    accent: str = "",
) -> QMenu:
    """프리스타일드 컨텍스트 메뉴 생성.

    Args:
        parent: 부모 위젯.
        items: 메뉴 항목 리스트. 각 항목:
            - ``("Label", callback)`` -- 일반 항목
            - ``("Label", callback, "danger")`` -- 위험 항목 (빨간색)
            - ``("Label", callback, "disabled")`` -- 비활성 항목
            - ``None`` -- 구분선
        accent: 선택 항목 배경 색상 (기본: c().SLATE).

    Returns:
        스타일링된 QMenu.

    Usage::

        menu = create_context_menu(self, [
            ("Open", self.on_open),
            ("Edit", self.on_edit),
            None,
            ("Export CSV", self.on_export),
            ("Delete", self.on_delete, "danger"),
            ("Locked", lambda: None, "disabled"),
        ])
        menu.exec(QCursor.pos())
    """
    hover_bg = accent if accent else c().SLATE

    menu = QMenu(parent)
    menu.setStyleSheet(_menu_qss(hover_bg))

    for entry in items:
        if entry is None:
            menu.addSeparator()
            continue

        label: str = entry[0]
        callback: Callable = entry[1]
        variant: str = entry[2] if len(entry) > 2 else ""

        action = QAction(label, menu)

        if variant == "danger":
            action.setProperty("menuVariant", "danger")
        elif variant == "disabled":
            action.setEnabled(False)

        action.triggered.connect(callback)
        menu.addAction(action)

    return menu


# ── QSS ──────────────────────────────────────────────


def _menu_qss(hover_bg: str) -> str:
    return (
        f"QMenu {{"
        f"  background: {c().NAVY};"
        f"  border: 1px solid {c().BORDER};"
        f"  border-radius: {Radius.SM}px;"
        f"  padding: 4px 0px;"
        f"  font-family: \"{Font.SANS}\";"
        f"  font-size: {Font.XS}px;"
        f"}}"
        f"QMenu::item {{"
        f"  color: {c().TEXT};"
        f"  padding: 6px 16px;"
        f"  border-radius: 4px;"
        f"  margin: 1px 4px;"
        f"}}"
        f"QMenu::item:selected {{"
        f"  background: {hover_bg};"
        f"}}"
        f"QMenu::item:disabled {{"
        f"  color: {c().DIM};"
        f"}}"
        # Danger variant via dynamic property
        f"QMenu::item[menuVariant=\"danger\"] {{"
        f"  color: {c().RED};"
        f"}}"
        f"QMenu::separator {{"
        f"  height: 1px;"
        f"  background: {c().BORDER};"
        f"  margin: 4px 8px;"
        f"}}"
    )
