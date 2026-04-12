"""
GeoView PySide6 — Theme Engine v7
==================================
Complete rewrite. 3-theme QSS: dark / light / beige
Neutral backgrounds, accent-only color, generous spacing, modern radii.
"""

from geoview_pyside6.constants import rgba
from geoview_pyside6.constants import (
    Category, CATEGORY_THEMES, Dark, Light, WarmBeige, SkyBlue, Font, Space, Radius
)

_THEME_MAP = {
    "dark": Dark,
    "light": Light,
    "beige": WarmBeige,
    "skyblue": SkyBlue,
}


def _generate_qss(mode: str = "beige", category: Category = Category.PROCESSING) -> str:
    c = _THEME_MAP.get(mode, WarmBeige)
    theme = CATEGORY_THEMES.get(category, CATEGORY_THEMES[Category.PROCESSING])
    accent = theme.accent
    accent_dim = theme.accent_dim

    # Determine button text color based on theme brightness
    btn_text = "#ffffff" if mode == "dark" else "#ffffff"

    return f"""
    /* ══════════════════════════════════════════
       GeoView Theme v7 — {mode} / {category.value}
       Neutral backgrounds + accent-only color
       ══════════════════════════════════════════ */

    /* ── Global Reset ── */
    QMainWindow {{
        background-color: {c.BG};
        color: {c.TEXT};
        font-family: {Font.SANS};
        font-size: {Font.BASE}px;
        line-height: 1.5;
    }}

    QWidget {{
        color: {c.TEXT};
        font-family: {Font.SANS};
        font-size: {Font.BASE}px;
    }}

    QLabel {{
        background: transparent;
        color: {c.TEXT};
    }}

    QFrame {{
        background: transparent;
    }}

    /* ══════════ SIDEBAR ══════════ */
    #sidebar {{
        background-color: {c.BG_ALT};
        border-right: 1px solid {c.BORDER};
    }}

    #sidebarBrand {{
        background: transparent;
        border-bottom: 1px solid {c.BORDER};
        padding: 0px;
    }}

    #brandLabel {{
        font-size: {Font.LG}px;
        font-weight: {Font.BOLD};
        color: {accent};
        letter-spacing: -0.4px;
        background: transparent;
    }}

    #versionLabel {{
        font-size: {Font.XS}px;
        color: {c.DIM};
        font-family: {Font.MONO};
    }}

    #sidebarButton {{
        background: transparent;
        color: {c.MUTED};
        border: none;
        border-left: 3px solid transparent;
        border-radius: {Radius.BASE}px;
        padding: 10px 14px 10px 14px;
        text-align: left;
        font-size: {Font.BASE}px;
        font-weight: {Font.REGULAR};
        margin: 1px {Space.SM}px;
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
        margin: {Space.SM}px {Space.BASE}px;
    }}

    #sidebarSectionLabel {{
        font-size: 10px;
        font-weight: {Font.SEMIBOLD};
        color: {c.DIM};
        padding: {Space.BASE}px {Space.BASE}px 6px {Space.BASE}px;
        text-transform: uppercase;
        letter-spacing: 1.2px;
        background: transparent;
    }}

    #collapseButton {{
        background: transparent;
        color: {c.DIM};
        border: 1px solid {c.BORDER};
        border-radius: {Radius.SM}px;
        font-size: 14px;
        margin: {Space.XS}px {Space.SM}px;
        padding: 4px;
    }}

    #collapseButton:hover {{
        background: {c.DARK};
        color: {c.TEXT};
        border-color: {c.BORDER_H};
    }}

    /* ── Sidebar Footer ── */
    #sidebarFooter {{
        border-top: 1px solid {c.BORDER};
        background: transparent;
    }}

    #sidebarFooterText {{
        font-size: {Font.XS}px;
        color: {c.DIM};
        background: transparent;
    }}

    /* ══════════ TOP BAR ══════════ */
    #topBar {{
        background-color: {c.BG_ALT};
        border-bottom: 1px solid {c.BORDER};
    }}

    #topBarTitle {{
        font-size: {Font.MD}px;
        font-weight: {Font.SEMIBOLD};
        color: {c.TEXT};
        letter-spacing: -0.2px;
    }}

    #contentStack {{
        background-color: {c.BG};
    }}

    /* ══════════ BUTTONS ══════════ */
    #primaryButton {{
        background-color: {accent};
        color: {btn_text};
        border: none;
        border-radius: {Radius.BASE}px;
        padding: 8px 20px;
        font-family: {Font.SANS};
        font-weight: {Font.MEDIUM};
        font-size: {Font.SM}px;
    }}
    #primaryButton:hover {{
        background-color: {rgba(accent, 0.87)};
    }}
    #primaryButton:pressed {{
        background-color: {rgba(accent, 0.73)};
    }}
    #primaryButton:focus {{
        border: 2px solid {rgba(accent, 0.38)};
    }}
    #primaryButton:disabled {{
        background-color: {c.SLATE};
        color: {c.DIM};
    }}

    #secondaryButton {{
        background-color: transparent;
        color: {c.TEXT};
        border: 1px solid {c.BORDER};
        border-radius: {Radius.BASE}px;
        padding: 8px 20px;
        font-family: {Font.SANS};
        font-size: {Font.SM}px;
    }}
    #secondaryButton:hover {{
        background-color: {c.DARK};
        border-color: {c.BORDER_H};
    }}
    #secondaryButton:focus {{
        border-color: {accent};
    }}

    #dangerButton {{
        background-color: {c.RED};
        color: #ffffff;
        border: none;
        border-radius: {Radius.BASE}px;
        padding: 8px 20px;
        font-family: {Font.SANS};
        font-size: {Font.SM}px;
        font-weight: {Font.MEDIUM};
    }}
    #dangerButton:hover {{
        background-color: {c.RED_H};
    }}

    #ghostButton {{
        background: transparent;
        color: {c.MUTED};
        border: none;
        border-radius: {Radius.BASE}px;
        padding: 8px 20px;
        font-family: {Font.SANS};
        font-size: {Font.SM}px;
    }}
    #ghostButton:hover {{
        background-color: {c.DARK};
        color: {c.TEXT};
    }}

    #languageButton {{
        background-color: transparent;
        color: {c.MUTED};
        border: 1px solid {c.BORDER};
        border-radius: {Radius.SM}px;
        padding: 4px 10px;
        font-family: {Font.SANS};
        font-size: {Font.XS}px;
        font-weight: {Font.MEDIUM};
    }}
    #languageButton:hover {{
        background-color: {c.DARK};
        color: {c.TEXT};
        border-color: {c.BORDER_H};
    }}

    /* ══════════ CARDS ══════════ */
    #gvCard {{
        background-color: {c.NAVY};
        border: 1px solid {c.BORDER};
        border-radius: {Radius.LG}px;
        padding: {Space.BASE}px {Space.LG}px;
    }}
    #gvCard:hover {{
        border-color: {c.BORDER_H};
    }}

    /* ══════════ KPI ══════════ */
    #kpiValue {{
        font-family: {Font.MONO};
        font-size: {Font.XL}px;
        font-weight: {Font.BOLD};
        color: {c.TEXT_BRIGHT};
        letter-spacing: -1px;
    }}

    #kpiLabel {{
        font-family: {Font.SANS};
        font-size: {Font.XS}px;
        font-weight: {Font.MEDIUM};
        color: {c.DIM};
        letter-spacing: 0.3px;
    }}

    /* ══════════ TABLES ══════════ */
    QTableView, QTreeView {{
        background-color: {c.BG};
        alternate-background-color: {c.BG_ALT};
        border: 1px solid {c.BORDER};
        border-radius: {Radius.BASE}px;
        gridline-color: {c.BORDER};
        selection-background-color: {accent_dim};
        selection-color: {c.TEXT_BRIGHT};
        font-size: {Font.BASE}px;
    }}

    QTableView::item {{
        padding: 8px 12px;
        border-bottom: 1px solid {c.BORDER};
        color: {c.TEXT};
    }}

    QTableView::item:hover {{
        background-color: {c.DARK};
    }}

    QTableView::item:selected {{
        background-color: {accent_dim};
        color: {c.TEXT_BRIGHT};
    }}

    QHeaderView::section {{
        background-color: {c.BG_ALT};
        color: {c.MUTED};
        font-weight: {Font.SEMIBOLD};
        font-size: {Font.XS}px;
        padding: 10px 12px;
        border: none;
        border-bottom: 1px solid {c.BORDER};
        border-right: 1px solid {c.BORDER};
        text-align: left;
        letter-spacing: 0.3px;
    }}

    /* ══════════ INPUT FIELDS ══════════ */
    QLineEdit, QTextEdit, QPlainTextEdit {{
        background-color: {c.DARK};
        color: {c.TEXT};
        border: 1px solid {c.BORDER};
        border-radius: {Radius.BASE}px;
        padding: 8px 12px;
        font-family: {Font.SANS};
        font-size: {Font.BASE}px;
        selection-background-color: {accent_dim};
    }}
    QLineEdit:hover, QTextEdit:hover {{
        border-color: {c.BORDER_H};
    }}
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
        border-color: {accent};
    }}
    QLineEdit::placeholder {{
        color: {c.DIM};
    }}

    /* ══════════ COMBOBOX ══════════ */
    QComboBox {{
        background-color: {c.DARK};
        color: {c.TEXT};
        border: 1px solid {c.BORDER};
        border-radius: {Radius.BASE}px;
        padding: 8px 12px;
        font-family: {Font.SANS};
        font-size: {Font.BASE}px;
    }}
    QComboBox:hover {{
        border-color: {c.BORDER_H};
    }}
    QComboBox:focus {{
        border-color: {accent};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 24px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {c.NAVY};
        color: {c.TEXT};
        border: 1px solid {c.BORDER};
        selection-background-color: {accent_dim};
        selection-color: {c.TEXT_BRIGHT};
        font-size: {Font.BASE}px;
        border-radius: {Radius.BASE}px;
    }}

    /* ══════════ TABS ══════════ */
    QTabWidget::pane {{
        border: 1px solid {c.BORDER};
        border-radius: {Radius.BASE}px;
        background-color: {c.BG};
    }}
    QTabBar::tab {{
        background-color: transparent;
        color: {c.MUTED};
        padding: 10px 24px;
        border-bottom: 2px solid transparent;
        font-family: {Font.SANS};
        font-size: {Font.BASE}px;
        font-weight: {Font.REGULAR};
    }}
    QTabBar::tab:hover {{
        color: {c.TEXT};
    }}
    QTabBar::tab:selected {{
        color: {accent};
        border-bottom-color: {accent};
        font-weight: {Font.MEDIUM};
    }}

    /* ══════════ DOCK WIDGETS ══════════ */
    QDockWidget {{
        background: {c.BG};
        color: {c.MUTED};
        font-size: {Font.SM}px;
        font-weight: {Font.MEDIUM};
        border: none;
    }}
    QDockWidget::title {{
        background: {c.BG_ALT};
        padding: 8px 12px;
        border-bottom: 1px solid {c.BORDER};
        border-left: 1px solid {c.BORDER};
        text-align: left;
    }}
    QDockWidget::close-button,
    QDockWidget::float-button {{
        background: transparent;
        border: none;
        icon-size: 14px;
        padding: 2px;
    }}
    QDockWidget::close-button:hover,
    QDockWidget::float-button:hover {{
        background: {c.DARK};
        border-radius: {Radius.XS}px;
    }}

    /* ══════════ SCROLLBARS (thin, minimal) ══════════ */
    QScrollBar:vertical {{
        background: transparent;
        width: 6px;
        margin: 2px;
    }}
    QScrollBar::handle:vertical {{
        background: {c.BORDER_H};
        border-radius: 3px;
        min-height: 28px;
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
        min-width: 28px;
    }}

    /* ══════════ PROGRESS BAR ══════════ */
    QProgressBar {{
        background-color: {c.DARK};
        border: none;
        border-radius: 3px;
        text-align: center;
        font-size: {Font.XS}px;
        color: {c.TEXT};
        max-height: 6px;
    }}
    QProgressBar::chunk {{
        background-color: {accent};
        border-radius: 3px;
    }}

    /* ══════════ STATUS BAR ══════════ */
    #gvStatusBar {{
        background-color: {c.BG_ALT};
        border: none;
        border-top: 1px solid {c.BORDER};
        color: {c.DIM};
        font-size: {Font.XS}px;
    }}
    QStatusBar::item {{
        border: none;
    }}

    /* ══════════ TOOLTIPS ══════════ */
    QToolTip {{
        background-color: {c.SURFACE};
        color: {c.TEXT};
        border: 1px solid {c.BORDER_H};
        border-radius: {Radius.SM}px;
        padding: 6px 10px;
        font-size: {Font.SM}px;
    }}

    /* ══════════ CONTEXT MENU ══════════ */
    QMenu {{
        background-color: {c.NAVY};
        color: {c.TEXT};
        border: 1px solid {c.BORDER};
        border-radius: {Radius.BASE}px;
        padding: {Space.XS}px 0px;
    }}
    QMenu::item {{
        padding: 8px 16px;
    }}
    QMenu::item:selected {{
        background-color: {c.DARK};
        color: {c.TEXT_BRIGHT};
    }}
    QMenu::item:disabled {{
        color: {c.DIM};
    }}
    QMenu::separator {{
        background-color: {c.BORDER};
        height: 1px;
        margin: {Space.XS}px {Space.SM}px;
    }}

    /* ══════════ SPLITTER ══════════ */
    QSplitter::handle {{
        background-color: {c.BORDER};
    }}
    QSplitter::handle:hover {{
        background-color: {accent};
    }}

    /* ══════════ STATUS BADGES ══════════ */
    #badgePass {{
        background-color: {rgba(c.GREEN, 0.1)};
        color: {c.GREEN};
        border-radius: {Radius.PILL}px;
        padding: 2px 10px;
        font-family: {Font.SANS};
        font-size: {Font.XS}px;
        font-weight: {Font.MEDIUM};
    }}
    #badgeWarn {{
        background-color: {rgba(c.ORANGE, 0.1)};
        color: {c.ORANGE};
        border-radius: {Radius.PILL}px;
        padding: 2px 10px;
        font-family: {Font.SANS};
        font-size: {Font.XS}px;
        font-weight: {Font.MEDIUM};
    }}
    #badgeFail {{
        background-color: {rgba(c.RED, 0.1)};
        color: {c.RED};
        border-radius: {Radius.PILL}px;
        padding: 2px 10px;
        font-family: {Font.SANS};
        font-size: {Font.XS}px;
        font-weight: {Font.MEDIUM};
    }}
    #badgeInfo {{
        background-color: {rgba(c.CYAN, 0.1)};
        color: {c.CYAN};
        border-radius: {Radius.PILL}px;
        padding: 2px 10px;
        font-family: {Font.SANS};
        font-size: {Font.XS}px;
        font-weight: {Font.MEDIUM};
    }}

    /* ══════════ SPINBOX ══════════ */
    QSpinBox, QDoubleSpinBox {{
        background-color: {c.DARK};
        color: {c.TEXT};
        border: 1px solid {c.BORDER};
        border-radius: {Radius.BASE}px;
        padding: 6px 8px;
        font-family: {Font.MONO};
        font-size: {Font.SM}px;
    }}
    QSpinBox:focus, QDoubleSpinBox:focus {{
        border-color: {accent};
    }}

    /* ══════════ CHECKBOX ══════════ */
    QCheckBox {{
        spacing: {Space.SM}px;
        font-size: {Font.BASE}px;
        color: {c.TEXT};
    }}
    QCheckBox::indicator {{
        width: 18px;
        height: 18px;
        border: 1px solid {c.BORDER_H};
        border-radius: {Radius.XS}px;
        background-color: {c.DARK};
    }}
    QCheckBox::indicator:hover {{
        border-color: {accent};
    }}
    QCheckBox::indicator:checked {{
        background-color: {accent};
        border-color: {accent};
    }}
    QCheckBox::indicator:disabled {{
        background-color: {c.SLATE};
        border-color: {c.BORDER};
    }}

    /* ══════════ RADIOBUTTON ══════════ */
    QRadioButton {{
        spacing: {Space.SM}px;
        font-size: {Font.BASE}px;
        color: {c.TEXT};
    }}
    QRadioButton::indicator {{
        width: 18px;
        height: 18px;
        border: 1px solid {c.BORDER_H};
        border-radius: 9px;
        background-color: {c.DARK};
    }}
    QRadioButton::indicator:hover {{
        border-color: {accent};
    }}
    QRadioButton::indicator:checked {{
        background-color: {accent};
        border-color: {accent};
    }}

    /* ══════════ GROUPBOX ══════════ */
    QGroupBox {{
        background-color: transparent;
        border: 1px solid {c.BORDER};
        border-radius: {Radius.BASE}px;
        margin-top: 14px;
        padding-top: {Space.BASE}px;
        font-family: {Font.SANS};
        font-size: {Font.BASE}px;
        font-weight: {Font.MEDIUM};
        color: {c.TEXT};
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: 12px;
        padding: 0px 6px;
        color: {c.MUTED};
    }}

    /* ══════════ SLIDER ══════════ */
    QSlider::groove:horizontal {{
        height: 4px;
        background: {c.SLATE};
        border-radius: 2px;
    }}
    QSlider::handle:horizontal {{
        width: 16px;
        height: 16px;
        margin: -6px 0;
        background: {accent};
        border-radius: 8px;
    }}
    QSlider::handle:horizontal:hover {{
        background: {rgba(accent, 0.87)};
    }}

    /* ══════════ FOCUS STATES ══════════ */
    #sidebarButton:focus {{
        border-left-color: {rgba(accent, 0.25)};
        background-color: {c.DARK};
    }}
    QComboBox:focus {{
        border-color: {accent};
    }}
    """


def get_extended_qss(mode: str = "beige", category: Category = Category.PROCESSING,
                     extra_qss: str = "") -> str:
    base = _generate_qss(mode, category)
    if extra_qss:
        return base + "\n" + extra_qss
    return base


def apply_theme(widget, mode: str = "beige", category: Category = Category.PROCESSING,
                extra_qss: str = ""):
    """위젯에 GeoView 테마 적용.
    Modes: 'dark' (Neutral Dark), 'light' (Clean Light), 'beige' (Warm Beige, default)
    """
    qss = get_extended_qss(mode, category, extra_qss)
    widget.setStyleSheet(qss)
