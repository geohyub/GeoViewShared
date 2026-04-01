"""
GeoView PySide6 — Design Constants
===================================
gv-tokens-v5.css와 동기화된 색상/폰트/스페이싱 상수.
웹(CSS)과 데스크톱(QSS)이 동일한 디자인 언어를 공유.
"""

from enum import Enum
from dataclasses import dataclass


# ════════════════════════════════════════════
# Category Identity
# ════════════════════════════════════════════

class Category(str, Enum):
    QC = "qc"
    PROCESSING = "processing"
    PREPROCESSING = "preprocessing"
    MANAGEMENT = "management"
    VALIDATION = "validation"
    UTILITIES = "utilities"
    AI = "ai"


@dataclass(frozen=True)
class CategoryTheme:
    accent: str
    accent_dim: str  # 10% opacity equivalent
    icon: str
    label_ko: str


CATEGORY_THEMES = {
    Category.QC:            CategoryTheme("#10B981", "#1a2f28", "🔍", "품질검사"),
    Category.PROCESSING:    CategoryTheme("#3B82F6", "#1a2436", "⚙️", "처리"),
    Category.PREPROCESSING: CategoryTheme("#F59E0B", "#2f2a1a", "🔄", "전처리"),
    Category.MANAGEMENT:    CategoryTheme("#8B5CF6", "#241a36", "📋", "관리"),
    Category.VALIDATION:    CategoryTheme("#06B6D4", "#1a2a2f", "✅", "검증"),
    Category.UTILITIES:     CategoryTheme("#64748B", "#1e2028", "🔧", "유틸"),
    Category.AI:            CategoryTheme("#F43F5E", "#2f1a20", "🤖", "AI"),
}


# ════════════════════════════════════════════
# Color Palette — Dark Theme (Default)
# ════════════════════════════════════════════

class Dark:
    # Surface (darkest → lightest)
    BG       = "#0A0E17"
    BG_ALT   = "#111827"
    DARK     = "#131A2B"
    NAVY     = "#1A2236"
    SLATE    = "#1E293B"
    SURFACE  = "#243044"

    # Text
    TEXT         = "#D1D5DB"
    TEXT_BRIGHT  = "#F9FAFB"
    MUTED        = "#6B7280"
    DIM          = "#4B5563"

    # Core Colors
    BLUE    = "#3B82F6"
    CYAN    = "#06B6D4"
    GREEN   = "#10B981"
    ORANGE  = "#F59E0B"
    RED     = "#EF4444"
    PURPLE  = "#8B5CF6"
    INDIGO  = "#6366F1"
    ROSE    = "#F43F5E"

    # Semantic
    SUCCESS = GREEN
    WARNING = ORANGE
    DANGER  = RED
    INFO    = CYAN

    # Hover states
    GREEN_H  = "#0ea572"
    CYAN_H   = "#0891b2"
    RED_H    = "#c0392b"
    BLUE_H   = "#2563eb"
    ORANGE_H = "#d97706"
    PURPLE_H = "#7c3aed"

    # Borders
    BORDER   = "#1F2937"
    BORDER_H = "#374151"

    # Shadows (not directly usable in QSS, but for reference)
    SHADOW = "rgba(0, 0, 0, 0.3)"


class Light:
    BG       = "#FAFBFC"
    BG_ALT   = "#F3F4F6"
    DARK     = "#E5E7EB"
    NAVY     = "#D1D5DB"
    SLATE    = "#F3F4F6"
    SURFACE  = "#FFFFFF"

    TEXT         = "#1F2937"
    TEXT_BRIGHT  = "#111827"
    MUTED        = "#6B7280"
    DIM          = "#9CA3AF"

    BLUE    = "#2563EB"
    CYAN    = "#0891B2"
    GREEN   = "#059669"
    ORANGE  = "#D97706"
    RED     = "#DC2626"
    PURPLE  = "#7C3AED"
    INDIGO  = "#4F46E5"
    ROSE    = "#E11D48"

    SUCCESS = GREEN
    WARNING = ORANGE
    DANGER  = RED
    INFO    = CYAN

    BORDER   = "#E5E7EB"
    BORDER_H = "#D1D5DB"

    SHADOW = "rgba(0, 0, 0, 0.08)"


# ════════════════════════════════════════════
# Typography
# ════════════════════════════════════════════

class Font:
    # Font families — 전부 Pretendard 통일
    SANS = "Pretendard"
    EN   = "Pretendard"
    MONO = "Pretendard"

    # Sizes (px) — 가독성과 절제의 균형
    XS   = 11
    SM   = 13
    BASE = 14
    MD   = 15
    LG   = 17
    XL   = 22
    XXL  = 26
    XXXL = 30

    # Weights
    REGULAR  = 400
    MEDIUM   = 500
    SEMIBOLD = 600
    BOLD     = 700
    BLACK    = 900


# ════════════════════════════════════════════
# Spacing (4px base grid)
# ════════════════════════════════════════════

class Space:
    XS  = 4
    SM  = 8
    MD  = 12
    BASE = 16
    LG  = 20
    XL  = 24
    XXL = 32
    XXXL = 40


# ════════════════════════════════════════════
# Border Radius
# ════════════════════════════════════════════

class Radius:
    SM   = 6
    BASE = 10
    LG   = 14
    XL   = 18
    PILL = 9999


# ════════════════════════════════════════════
# Accent Colors (NavQC Gold family)
# ════════════════════════════════════════════

class Accent:
    GOLD       = "#D4A843"
    GOLD_HOVER = "#E0B854"
    GOLD_DIM   = "#D4A84340"


# ════════════════════════════════════════════
# Status Icons (접근성: 색상 + 텍스트 아이콘)
# ════════════════════════════════════════════

STATUS_ICONS = {
    "PASS": "\u2713",      # ✓
    "WARNING": "\u26A0",   # ⚠
    "FAIL": "\u2717",      # ✗
    "N/A": "\u2014",       # —
    "INFO": "\u2139",      # ℹ
    "DONE": "\u2713",      # ✓
    "ERROR": "\u2717",     # ✗
    "RUNNING": "\u25B6",   # ▶
}


# ════════════════════════════════════════════
# Common QSS Templates
# ════════════════════════════════════════════

TABLE_HEADER_STYLE = f"""
    QHeaderView::section {{
        background: {Dark.NAVY};
        color: {Dark.MUTED};
        font-size: {Font.XS}px;
        font-weight: {Font.MEDIUM};
        border: none;
        border-bottom: 1px solid {Dark.BORDER};
        padding: 6px 8px;
    }}
"""

TABLE_STYLE = f"""
    QTableWidget {{
        background: {Dark.BG};
        alternate-background-color: {Dark.BG_ALT};
        color: {Dark.TEXT};
        border: 1px solid {Dark.BORDER};
        border-radius: {Radius.SM}px;
        font-size: {Font.XS}px;
        gridline-color: {Dark.BORDER};
    }}
    QTableWidget::item {{
        padding: 4px 8px;
    }}
    QTableWidget::item:selected {{
        background: {Dark.SLATE};
    }}
    {TABLE_HEADER_STYLE}
"""

BTN_PRIMARY = f"""
    QPushButton {{
        background: {Dark.GREEN};
        color: {Dark.BG};
        border: none;
        border-radius: {Radius.SM}px;
        font-size: {Font.SM}px;
        font-weight: {Font.SEMIBOLD};
        padding: 6px 16px;
    }}
    QPushButton:hover {{ background: {Dark.GREEN_H}; }}
    QPushButton:disabled {{
        background: {Dark.SLATE};
        color: {Dark.DIM};
    }}
"""

BTN_SECONDARY = f"""
    QPushButton {{
        background: transparent;
        color: {Dark.MUTED};
        border: 1px solid {Dark.BORDER};
        border-radius: {Radius.SM}px;
        font-size: {Font.SM}px;
        padding: 6px 16px;
    }}
    QPushButton:hover {{
        background: {Dark.DARK};
        color: {Dark.TEXT};
        border-color: {Dark.BORDER_H};
    }}
"""

BTN_DANGER = f"""
    QPushButton {{
        background: {Dark.RED};
        color: white;
        border: none;
        border-radius: {Radius.SM}px;
        font-size: {Font.XS}px;
        padding: 4px 12px;
    }}
    QPushButton:hover {{ background: {Dark.RED_H}; }}
"""
