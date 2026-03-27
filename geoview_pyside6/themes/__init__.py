"""
GeoView PySide6 — Theme Engine v2
==================================
QSS 기반 테마 시스템. 절제된 크기, 세련된 색상, 깊이감 있는 카드 디자인.
"""

from pathlib import Path
from geoview_pyside6.constants import (
    Category, CATEGORY_THEMES, Dark, Light, Font, Space, Radius
)


def _generate_qss(mode: str = "dark", category: Category = Category.PROCESSING) -> str:
    """동적 QSS 생성 — 모드와 카테고리에 따라 색상 적용."""

    c = Dark if mode == "dark" else Light
    theme = CATEGORY_THEMES.get(category, CATEGORY_THEMES[Category.PROCESSING])
    accent = theme.accent
    accent_dim = theme.accent_dim

    return f"""
    /* ══════════════════════════════════════════
       GeoView PySide6 Theme v2 — {mode.upper()} / {category.value}
       ══════════════════════════════════════════ */

    /* ── Global ── */
    QMainWindow, QWidget {{
        background-color: {c.BG};
        color: {c.TEXT};
        font-family: {Font.SANS};
        font-size: {Font.BASE}px;
    }}

    QLabel {{
        background: transparent;
    }}

    /* ── Sidebar ── */
    #sidebar {{
        background-color: {c.BG_ALT};
        border-right: 1px solid {c.BORDER};
    }}

    #sidebarBrand {{
        background: transparent;
        border-bottom: 1px solid {c.BORDER};
    }}

    #brandLabel {{
        font-size: {Font.LG}px;
        font-weight: {Font.BOLD};
        color: {accent};
        letter-spacing: -0.3px;
    }}

    #versionLabel {{
        font-size: {Font.XS}px;
        color: {c.DIM};
    }}

    #sidebarButton {{
        background: transparent;
        color: {c.MUTED};
        border: none;
        border-left: 3px solid transparent;
        border-radius: 0px;
        padding: 9px {Space.MD}px 9px {Space.BASE}px;
        text-align: left;
        font-size: {Font.SM}px;
    }}

    #sidebarButton:hover {{
        background-color: {c.DARK};
        color: {c.TEXT};
        border-left-color: {c.BORDER_H};
    }}

    #sidebarButton:checked {{
        background-color: {accent_dim};
        color: {accent};
        font-weight: {Font.MEDIUM};
        border-left-color: {accent};
    }}

    #sidebarDivider {{
        background-color: {c.BORDER};
        max-height: 1px;
        margin: {Space.SM}px {Space.MD}px;
    }}

    #sidebarSectionLabel {{
        font-size: {Font.XS}px;
        color: {c.DIM};
        padding-left: {Space.MD}px;
        text-transform: uppercase;
        letter-spacing: 1px;
    }}

    /* ── Top Bar ── */
    #topBar {{
        background-color: {c.BG_ALT};
        border-bottom: 1px solid {c.BORDER};
    }}

    #topBarTitle {{
        font-family: {Font.SANS};
        font-size: {Font.MD}px;
        font-weight: {Font.MEDIUM};
        color: {c.TEXT_BRIGHT};
        letter-spacing: -0.2px;
    }}

    /* ── Buttons ── */
    #primaryButton {{
        background-color: {accent};
        color: #FFFFFF;
        border: none;
        border-radius: {Radius.SM}px;
        padding: 6px {Space.BASE}px;
        font-family: {Font.SANS};
        font-weight: {Font.MEDIUM};
        font-size: {Font.SM}px;
    }}

    #primaryButton:hover {{
        background-color: {accent}DD;
    }}

    #primaryButton:pressed {{
        background-color: {accent}BB;
    }}

    #secondaryButton {{
        background-color: transparent;
        color: {c.MUTED};
        border: 1px solid {c.BORDER};
        border-radius: {Radius.SM}px;
        padding: 6px {Space.BASE}px;
        font-family: {Font.SANS};
        font-size: {Font.SM}px;
    }}

    #secondaryButton:hover {{
        background-color: {c.DARK};
        border-color: {c.BORDER_H};
        color: {c.TEXT};
    }}

    /* ── Cards ── */
    #gvCard {{
        background-color: {c.NAVY};
        border: 1px solid {c.BORDER};
        border-radius: {Radius.SM}px;
        padding: {Space.BASE}px {Space.LG}px;
    }}

    #gvCard:hover {{
        border-color: {c.BORDER_H};
    }}

    /* ── KPI Card ── */
    #kpiValue {{
        font-family: {Font.MONO};
        font-size: {Font.XL}px;
        font-weight: {Font.SEMIBOLD};
        color: {c.TEXT_BRIGHT};
        letter-spacing: -0.5px;
    }}

    #kpiLabel {{
        font-family: {Font.SANS};
        font-size: {Font.XS}px;
        color: {c.DIM};
        letter-spacing: 0.3px;
    }}

    /* ── Tables ── */
    QTableView, QTreeView {{
        background-color: {c.DARK};
        alternate-background-color: {c.NAVY};
        border: 1px solid {c.BORDER};
        border-radius: {Radius.SM}px;
        gridline-color: {c.BORDER};
        selection-background-color: {accent_dim};
        selection-color: {c.TEXT_BRIGHT};
        font-size: {Font.SM}px;
    }}

    QTableView::item {{
        padding: 5px {Space.SM}px;
        border-bottom: 1px solid {c.BORDER};
    }}

    QTableView::item:hover {{
        background-color: {c.NAVY};
    }}

    QTableView::item:selected {{
        background-color: {accent_dim};
    }}

    QHeaderView::section {{
        background-color: {c.BG_ALT};
        color: {c.DIM};
        font-weight: {Font.MEDIUM};
        font-size: {Font.XS}px;
        padding: 6px {Space.SM}px;
        border: none;
        border-bottom: 1px solid {c.BORDER};
        border-right: 1px solid {c.BORDER};
        text-align: left;
    }}

    /* ── Input Fields ── */
    QLineEdit, QTextEdit, QPlainTextEdit {{
        background-color: {c.DARK};
        color: {c.TEXT};
        border: 1px solid {c.BORDER};
        border-radius: {Radius.SM}px;
        padding: 6px {Space.SM}px;
        font-family: {Font.SANS};
        font-size: {Font.SM}px;
        selection-background-color: {accent_dim};
    }}

    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
        border-color: {accent};
    }}

    QLineEdit::placeholder {{
        color: {c.DIM};
    }}

    /* ── ComboBox ── */
    QComboBox {{
        background-color: {c.DARK};
        color: {c.TEXT};
        border: 1px solid {c.BORDER};
        border-radius: {Radius.SM}px;
        padding: 6px {Space.SM}px;
        font-family: {Font.SANS};
        font-size: {Font.SM}px;
    }}

    QComboBox:hover {{
        border-color: {c.BORDER_H};
    }}

    QComboBox::drop-down {{
        border: none;
        width: 20px;
    }}

    QComboBox QAbstractItemView {{
        background-color: {c.NAVY};
        color: {c.TEXT};
        border: 1px solid {c.BORDER};
        selection-background-color: {accent_dim};
        selection-color: {c.TEXT_BRIGHT};
        font-size: {Font.SM}px;
    }}

    /* ── Tab Widget ── */
    QTabWidget::pane {{
        border: 1px solid {c.BORDER};
        border-radius: {Radius.SM}px;
        background-color: {c.BG};
    }}

    QTabBar::tab {{
        background-color: transparent;
        color: {c.DIM};
        padding: 7px {Space.LG}px;
        border-bottom: 2px solid transparent;
        font-family: {Font.SANS};
        font-size: {Font.SM}px;
    }}

    QTabBar::tab:hover {{
        color: {c.TEXT};
    }}

    QTabBar::tab:selected {{
        color: {accent};
        border-bottom-color: {accent};
        font-weight: {Font.MEDIUM};
    }}

    /* ── ScrollBars ── */
    QScrollBar:vertical {{
        background: transparent;
        width: 6px;
        margin: 2px;
    }}

    QScrollBar::handle:vertical {{
        background: {c.BORDER_H};
        border-radius: 3px;
        min-height: 24px;
    }}

    QScrollBar::handle:vertical:hover {{
        background: {c.MUTED};
    }}

    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}

    QScrollBar:horizontal {{
        background: transparent;
        height: 6px;
        margin: 2px;
    }}

    QScrollBar::handle:horizontal {{
        background: {c.BORDER_H};
        border-radius: 3px;
        min-width: 24px;
    }}

    /* ── Progress Bar ── */
    QProgressBar {{
        background-color: {c.DARK};
        border: none;
        border-radius: 2px;
        text-align: center;
        font-size: {Font.XS}px;
        color: {c.TEXT};
    }}

    QProgressBar::chunk {{
        background-color: {accent};
        border-radius: 2px;
    }}

    /* ── Status Bar ── */
    #gvStatusBar {{
        background-color: {c.BG_ALT};
        border-top: 1px solid {c.BORDER};
        color: {c.DIM};
        font-size: {Font.XS}px;
    }}

    /* ── Tooltips ── */
    QToolTip {{
        background-color: {c.SURFACE};
        color: {c.TEXT};
        border: 1px solid {c.BORDER_H};
        border-radius: 4px;
        padding: 4px 8px;
        font-size: {Font.XS}px;
    }}

    /* ── Splitter ── */
    QSplitter::handle {{
        background-color: {c.BORDER};
    }}

    QSplitter::handle:hover {{
        background-color: {c.BORDER_H};
    }}

    /* ── Status Badges ── */
    #badgePass {{
        background-color: {c.GREEN}1A;
        color: {c.GREEN};
        border-radius: {Radius.PILL}px;
        padding: 1px 6px;
        font-family: {Font.EN};
        font-size: {Font.XS}px;
        font-weight: {Font.MEDIUM};
    }}

    #badgeWarn {{
        background-color: {c.ORANGE}1A;
        color: {c.ORANGE};
        border-radius: {Radius.PILL}px;
        padding: 1px 6px;
        font-family: {Font.EN};
        font-size: {Font.XS}px;
        font-weight: {Font.MEDIUM};
    }}

    #badgeFail {{
        background-color: {c.RED}1A;
        color: {c.RED};
        border-radius: {Radius.PILL}px;
        padding: 1px 6px;
        font-family: {Font.EN};
        font-size: {Font.XS}px;
        font-weight: {Font.MEDIUM};
    }}

    #badgeInfo {{
        background-color: {c.CYAN}1A;
        color: {c.CYAN};
        border-radius: {Radius.PILL}px;
        padding: 1px 6px;
        font-family: {Font.EN};
        font-size: {Font.XS}px;
        font-weight: {Font.MEDIUM};
    }}

    /* ── SpinBox ── */
    QSpinBox, QDoubleSpinBox {{
        background-color: {c.DARK};
        color: {c.TEXT};
        border: 1px solid {c.BORDER};
        border-radius: {Radius.SM}px;
        padding: 4px 6px;
        font-family: {Font.MONO};
        font-size: {Font.SM}px;
    }}

    QSpinBox:focus, QDoubleSpinBox:focus {{
        border-color: {accent};
    }}
    """


def apply_theme(widget, mode: str = "dark", category: Category = Category.PROCESSING):
    """위젯에 GeoView 테마 적용."""
    qss = _generate_qss(mode, category)
    widget.setStyleSheet(qss)
