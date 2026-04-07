"""
GeoView PySide6 — Design Constants v6
======================================
3-theme system: Ocean Teal (dark) / Clean Light / Warm Beige
Tokens sourced from: shadcn/ui, GitHub Primer, Vercel Geist, Linear
All class names & attribute names are STABLE — only values change.
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
    Category.QC:            CategoryTheme("#3b82f6", "#3b82f612", "QC", "품질검사"),
    Category.PROCESSING:    CategoryTheme("#3b82f6", "#3b82f612", "PR", "처리"),
    Category.PREPROCESSING: CategoryTheme("#fbbf24", "#fbbf2412", "PP", "전처리"),
    Category.MANAGEMENT:    CategoryTheme("#a78bfa", "#a78bfa12", "MG", "관리"),
    Category.VALIDATION:    CategoryTheme("#14b8a6", "#14b8a612", "VL", "검증"),
    Category.UTILITIES:     CategoryTheme("#64748b", "#64748b12", "UT", "유틸"),
    Category.AI:            CategoryTheme("#fb7185", "#fb718512", "AI", "AI"),
}


# ════════════════════════════════════════════
# Color Palette — Dark Theme (Default)
# ════════════════════════════════════════════

class Dark:
    """Neutral Dark — 순수 중립 그레이 배경 + teal 악센트만."""
    # Surface — 완전 중립 (Linear/shadcn 스타일, 색조 없음)
    BG       = "#0c0c0e"   # near-black, 완전 중립
    BG_ALT   = "#141416"   # sidebar / topbar
    DARK     = "#1a1a1e"   # input fields, card inner
    NAVY     = "#202024"   # card background, table header
    SLATE    = "#28282e"   # hover state, elevated
    SURFACE  = "#2e2e34"   # popover, tooltip

    # Text — 따뜻한 off-white (순백 아님, 눈 피로 감소)
    TEXT         = "#e4e4e8"   # primary text
    TEXT_BRIGHT  = "#f4f4f6"   # headings, KPI values
    MUTED        = "#8e8e96"   # secondary text, legends
    DIM          = "#5c5c64"   # tertiary, axis labels

    # Core Colors
    BLUE    = "#3b82f6"
    CYAN    = "#14b8a6"    # teal (GeoView accent — 버튼/링크/활성 탭만)
    GREEN   = "#34d399"    # success / pass
    ORANGE  = "#fbbf24"    # warning
    RED     = "#f87171"    # danger / fail
    PURPLE  = "#a78bfa"
    INDIGO  = "#6366f1"
    ROSE    = "#fb7185"

    # Semantic
    SUCCESS = GREEN
    WARNING = ORANGE
    DANGER  = RED
    INFO    = CYAN

    # Hover states
    GREEN_H  = "#6ee7b7"
    CYAN_H   = "#2dd4bf"
    RED_H    = "#fca5a5"
    BLUE_H   = "#60a5fa"
    ORANGE_H = "#fcd34d"
    PURPLE_H = "#c4b5fd"

    # Borders — 중립 그레이
    BORDER   = "#252528"   # normal
    BORDER_H = "#363639"   # hover

    # Chart-specific
    CROSSHAIR    = "#ffffff80"
    CHART_BG     = "#141416"
    CHART_GRID   = "#252528"
    STATS_BOX_BG = "#202024"
    STATS_BOX_BORDER = "#363639"

    # Shadows
    SHADOW = "rgba(0, 0, 0, 0.3)"


class Light:
    """Clean Light — Vercel Geist-inspired, crisp white, high contrast."""
    BG       = "#ffffff"
    BG_ALT   = "#fafafa"
    DARK     = "#f5f5f5"   # input bg, subtle card
    NAVY     = "#f0f0f0"   # card background
    SLATE    = "#e5e5e5"   # hover, elevated
    SURFACE  = "#ffffff"   # popover, tooltip

    TEXT         = "#171717"   # near-black
    TEXT_BRIGHT  = "#0a0a0a"   # headings
    MUTED        = "#666666"   # secondary
    DIM          = "#a3a3a3"   # tertiary

    BLUE    = "#0070f3"
    CYAN    = "#0d9488"    # teal-600 (GeoView marine)
    GREEN   = "#17c964"
    ORANGE  = "#f5a623"
    RED     = "#e5484d"
    PURPLE  = "#7c3aed"
    INDIGO  = "#4f46e5"
    ROSE    = "#e11d48"

    SUCCESS = GREEN
    WARNING = ORANGE
    DANGER  = RED
    INFO    = CYAN

    GREEN_H  = "#13a452"
    CYAN_H   = "#0f766e"
    RED_H    = "#c53030"
    BLUE_H   = "#0060df"
    ORANGE_H = "#d4901e"
    PURPLE_H = "#6d28d9"

    BORDER   = "#eaeaea"
    BORDER_H = "#d4d4d4"

    CROSSHAIR    = "#00000050"
    CHART_BG     = "#fafafa"
    CHART_GRID   = "#eaeaea"
    STATS_BOX_BG = "#ffffff"
    STATS_BOX_BORDER = "#eaeaea"

    SHADOW = "rgba(0, 0, 0, 0.06)"


class SkyBlue:
    """Sky Blue — 밝은 하늘색/푸른빛 테마. 시원하고 깔끔."""
    BG       = "#f0f5fa"   # very pale blue
    BG_ALT   = "#e6eef6"   # slightly deeper pale blue
    DARK     = "#dce6f0"   # input bg
    NAVY     = "#f5f8fc"   # card background (lighter than bg)
    SLATE    = "#d0dcea"   # hover
    SURFACE  = "#f5f8fc"   # popover

    TEXT         = "#1a2332"   # dark navy text
    TEXT_BRIGHT  = "#0d1520"   # headings
    MUTED        = "#546478"   # secondary
    DIM          = "#8c9aac"   # tertiary

    BLUE    = "#2563eb"
    CYAN    = "#0d9488"    # GeoView teal accent
    GREEN   = "#059669"
    ORANGE  = "#d97706"
    RED     = "#dc2626"
    PURPLE  = "#7c3aed"
    INDIGO  = "#4f46e5"
    ROSE    = "#e11d48"

    SUCCESS = GREEN
    WARNING = ORANGE
    DANGER  = RED
    INFO    = CYAN

    GREEN_H  = "#047857"
    CYAN_H   = "#0f766e"
    RED_H    = "#b91c1c"
    BLUE_H   = "#1d4ed8"
    ORANGE_H = "#b45309"
    PURPLE_H = "#6d28d9"

    BORDER   = "#c8d6e5"   # soft blue border
    BORDER_H = "#a8bcd0"   # hover border

    CROSSHAIR    = "#1a233260"
    CHART_BG     = "#f5f8fc"
    CHART_GRID   = "#c8d6e5"
    STATS_BOX_BG = "#f5f8fc"
    STATS_BOX_BORDER = "#c8d6e5"

    SHADOW = "rgba(30, 60, 100, 0.06)"


class WarmBeige:
    """Warm Beige — paper-like, minimal eye strain, teal accent."""
    BG       = "#f5f0e8"
    BG_ALT   = "#ede8df"
    DARK     = "#e8e3da"   # input bg
    NAVY     = "#faf6f0"   # card background (lighter than bg)
    SLATE    = "#e0dbd2"   # hover
    SURFACE  = "#faf6f0"   # popover

    TEXT         = "#2c2418"   # warm dark brown
    TEXT_BRIGHT  = "#1a1208"   # headings
    MUTED        = "#6b5e4e"   # secondary
    DIM          = "#9e9282"   # tertiary

    BLUE    = "#4f6df5"
    CYAN    = "#0d9488"    # teal (GeoView marine)
    GREEN   = "#059669"
    ORANGE  = "#d97706"
    RED     = "#dc2626"
    PURPLE  = "#7c3aed"
    INDIGO  = "#4f46e5"
    ROSE    = "#e11d48"

    SUCCESS = GREEN
    WARNING = ORANGE
    DANGER  = RED
    INFO    = CYAN

    GREEN_H  = "#047857"
    CYAN_H   = "#0f766e"
    RED_H    = "#b91c1c"
    BLUE_H   = "#3b5ee0"
    ORANGE_H = "#b45309"
    PURPLE_H = "#6d28d9"

    BORDER   = "#d8d0c4"   # warm border
    BORDER_H = "#c4baa8"   # hover border

    CROSSHAIR    = "#2c241860"
    CHART_BG     = "#faf6f0"
    CHART_GRID   = "#d8d0c4"
    STATS_BOX_BG = "#faf6f0"
    STATS_BOX_BORDER = "#d8d0c4"

    SHADOW = "rgba(100, 80, 50, 0.06)"


# ════════════════════════════════════════════
# Typography
# ════════════════════════════════════════════

class Font:
    # Font families — Pretendard: modern Korean UI font (fallback chain)
    SANS = "Pretendard, 'Wanted Sans Std', -apple-system, 'Segoe UI', sans-serif"
    EN   = "Pretendard, 'Wanted Sans Std', -apple-system, 'Segoe UI', sans-serif"
    MONO = "'JetBrains Mono', Consolas, 'Cascadia Code', monospace"

    # Sizes (px) — 업계 표준 스케일 (Inter/Geist 기준)
    XS   = 11
    SM   = 12
    BASE = 13
    MD   = 14
    LG   = 16
    XL   = 20
    XXL  = 24
    XXXL = 30

    # Weights
    REGULAR  = 400
    MEDIUM   = 500
    SEMIBOLD = 600
    BOLD     = 700
    BLACK    = 900

    # Line heights (multiplier)
    LINE_XS   = 1.3
    LINE_SM   = 1.4
    LINE_BASE = 1.5
    LINE_LG   = 1.4
    LINE_XL   = 1.3
    LINE_XXL  = 1.2

    # Letter-spacing (per size tier — larger text tighter, smaller text wider)
    TRACK_XS   = "0.5px"    # 11px — wider (captions, badges)
    TRACK_SM   = "0.2px"    # 13px — slightly wider
    TRACK_BASE = "0px"      # 14px — normal
    TRACK_LG   = "-0.2px"   # 17px — slightly tight
    TRACK_XL   = "-0.5px"   # 22px — tight (subheadings)
    TRACK_XXL  = "-0.8px"   # 26px — tighter (main headings)
    TRACK_HERO = "-1.5px"   # 30px+ — very tight (hero text)


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
    XS   = 4
    SM   = 6
    BASE = 8     # 업계 표준 기본값 (8px)
    LG   = 12    # 카드, 패널
    XL   = 16    # 모달, 큰 컨테이너
    PILL = 9999


# ════════════════════════════════════════════
# Accent Colors (NavQC Gold family)
# ════════════════════════════════════════════

class Accent:
    GOLD       = "#D4A843"
    GOLD_HOVER = "#E0B854"
    GOLD_DIM   = "#D4A84340"


# ════════════════════════════════════════════
# Opacity (hex suffix for color strings)
# ════════════════════════════════════════════

class Opacity:
    """투명도 hex 접미어.

    WARNING: QSS에서 `f"{c().COLOR}{Opacity.LOW}"` 형태로 사용하면
    Qt가 #AARRGGBB로 해석하여 의도와 다른 색상이 됩니다.
    반드시 rgba() 헬퍼를 사용하세요:
        rgba(c().GREEN, 0.1)   # 올바름
        f"{c().GREEN}1A"       # 잘못됨 — 사용 금지
    """
    SUBTLE  = "0D"   # 5%
    LOW     = "1A"   # 10%  — 배지 배경, 선택 영역
    MEDIUM  = "40"   # 25%  — 비활성 아이콘, 보조 테두리
    HIGH    = "80"   # 50%  — 포커스 링, 오버레이
    HEAVY   = "BF"   # 75%  — 강조 배경
    HOVER   = "DD"   # 87%  — 버튼 hover
    PRESSED = "BB"   # 73%  — 버튼 pressed
    FULL    = "FF"   # 100%


def rgba(hex_color: str, alpha: float) -> str:
    """Convert #RRGGBB + alpha(0.0~1.0) → 'rgba(r,g,b,a)' for QSS.

    Qt QSS에서 hex8(#RRGGBBAA)은 #AARRGGBB로 해석되므로,
    반투명 색상은 반드시 이 함수를 통해 rgba() 형식으로 변환하세요.

    Usage:
        rgba(c().GREEN, 0.1)   → "rgba(52, 211, 153, 0.1)"
        rgba(c().RED, 0.25)    → "rgba(229, 72, 77, 0.25)"
    """
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)
    return f"rgba({r}, {g}, {b}, {alpha})"


# ════════════════════════════════════════════
# Device Status Colors (PortDetector/Network)
# ════════════════════════════════════════════

class DeviceColors:
    """네트워크 디바이스 상태 색상 (PortDetector 등)."""
    CONNECTED    = "#06d6a0"
    DISCONNECTED = "#ef476f"
    DELAYED      = "#ffd166"
    FILTERED     = "#ffd166"
    UNKNOWN      = "#6a6a8a"


# ════════════════════════════════════════════
# Status Icons (접근성: 색상 + 텍스트 아이콘)
# ════════════════════════════════════════════

STATUS_ICONS = {
    "PASS": "V",           # checkmark (ASCII-safe)
    "WARNING": "!",        # warning (ASCII-safe)
    "FAIL": "X",           # cross (ASCII-safe)
    "N/A": "-",            # dash (ASCII-safe)
    "INFO": "i",           # info (ASCII-safe)
    "DONE": "V",           # checkmark (ASCII-safe)
    "ERROR": "X",          # cross (ASCII-safe)
    "RUNNING": ">",        # play (ASCII-safe)
}


# ════════════════════════════════════════════
# Common QSS Templates
# ════════════════════════════════════════════

TABLE_HEADER_STYLE = f"""
    QHeaderView::section {{
        background: {Dark.NAVY};
        color: {Dark.DIM};
        font-size: {Font.XS}px;
        font-weight: {Font.SEMIBOLD};
        border: none;
        border-bottom: 1px solid {Dark.BORDER};
        padding: 8px 12px;
        letter-spacing: 0.3px;
    }}
"""

TABLE_STYLE = f"""
    QTableWidget {{
        background: {Dark.BG};
        alternate-background-color: {Dark.BG_ALT};
        color: {Dark.TEXT};
        border: 1px solid {Dark.BORDER};
        border-radius: {Radius.BASE}px;
        font-size: {Font.SM}px;
        gridline-color: {Dark.BORDER};
    }}
    QTableWidget::item {{
        padding: 6px 12px;
    }}
    QTableWidget::item:selected {{
        background: {Dark.SLATE};
    }}
    QTableWidget::item:hover {{
        background: {Dark.DARK};
    }}
    {TABLE_HEADER_STYLE}
"""

BTN_PRIMARY = f"""
    QPushButton {{
        background: {Dark.CYAN};
        color: #ffffff;
        border: none;
        border-radius: {Radius.BASE}px;
        font-size: {Font.SM}px;
        font-weight: {Font.MEDIUM};
        padding: 7px 18px;
    }}
    QPushButton:hover {{ background: {Dark.CYAN_H}; }}
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
        border-radius: {Radius.BASE}px;
        font-size: {Font.SM}px;
        padding: 7px 18px;
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
        border-radius: {Radius.BASE}px;
        font-size: {Font.XS}px;
        padding: 5px 14px;
    }}
    QPushButton:hover {{ background: {Dark.RED_H}; }}
"""
