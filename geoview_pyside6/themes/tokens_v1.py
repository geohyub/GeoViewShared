"""
tokens_v1 — CPT 3 앱 전용 디자인 토큰 (Wave 6 B1.2)

참조 단일 소스: plans/design_tokens_v1.md
적용 앱: CPTPrep / CPTQC / CPTProc (Phase B Wave 1~3)
기존 themes/ 엔진과 공존. 기존 Dark/Light/WarmBeige 는 건드리지 않음.

규율 (wave6_b1_cptprep_plan.md §0.3):
- 본 파일은 신규 추가. 기존 themes/__init__.py 수정 금지.
- raw hex 직접 사용 금지. 모든 참조는 tokens 에서.
- 3 팔레트 (Subaqua Pro / Minimal Graphite / Korean Earth) 런타임 전환 가능.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

PaletteName = Literal["subaqua_pro", "minimal_graphite", "korean_earth"]


@dataclass(frozen=True)
class Palette:
    name: str
    bg_base: str
    bg_surface: str
    bg_elevated: str
    border_subtle: str
    border_strong: str
    text_primary: str
    text_secondary: str
    text_disabled: str
    accent_primary: str
    accent_muted: str
    status_pass: str
    status_suspect: str
    status_fail: str
    status_info: str


SUBAQUA_PRO = Palette(
    name="subaqua_pro",
    bg_base="#0F1A2E",
    bg_surface="#152238",
    bg_elevated="#1B2B45",
    border_subtle="#23314C",
    border_strong="#2F4163",
    text_primary="#E8EEF8",
    text_secondary="#9BAAC4",
    text_disabled="#5C6B85",
    accent_primary="#4FD4FF",
    accent_muted="#2E7FA8",
    status_pass="#4ADE80",
    status_suspect="#FBBF24",
    status_fail="#F87171",
    status_info="#60A5FA",
)

MINIMAL_GRAPHITE = Palette(
    name="minimal_graphite",
    bg_base="#F7F8FA",
    bg_surface="#FFFFFF",
    bg_elevated="#FFFFFF",
    border_subtle="#E5E7EB",
    border_strong="#D1D5DB",
    text_primary="#111827",
    text_secondary="#4B5563",
    text_disabled="#9CA3AF",
    accent_primary="#111827",
    accent_muted="#374151",
    status_pass="#16A34A",
    status_suspect="#D97706",
    status_fail="#DC2626",
    status_info="#2563EB",
)

KOREAN_EARTH = Palette(
    name="korean_earth",
    bg_base="#FAF7F2",
    bg_surface="#FFFFFF",
    bg_elevated="#FFFFFF",
    border_subtle="#D9D2C5",
    border_strong="#B8AE9C",
    text_primary="#1C1917",
    text_secondary="#57534E",
    text_disabled="#A8A29E",
    accent_primary="#C2410C",
    accent_muted="#9A3412",
    status_pass="#16A34A",
    status_suspect="#D97706",
    status_fail="#DC2626",
    status_info="#2563EB",
)

PALETTES: dict[PaletteName, Palette] = {
    "subaqua_pro": SUBAQUA_PRO,
    "minimal_graphite": MINIMAL_GRAPHITE,
    "korean_earth": KOREAN_EARTH,
}


@dataclass(frozen=True)
class Sizes:
    row_sidebar: int = 28
    row_table: int = 32
    row_table_header: int = 36
    card_kpi: int = 88
    indent_tree: int = 16
    border_default: int = 1
    stripe_status: int = 4
    handle_splitter: int = 4
    scrollbar_width: int = 10
    scrollbar_thumb: int = 6
    focus_outline: int = 2
    focus_offset: int = 2
    radius_sm: int = 2
    radius_md: int = 4


@dataclass(frozen=True)
class Space:
    x0: int = 0
    x1: int = 4
    x2: int = 8
    x3: int = 12
    x4: int = 16
    x5: int = 20
    x6: int = 24
    x8: int = 32
    x9: int = 36
    x11: int = 44
    x14: int = 56
    x18: int = 72
    x22: int = 88


@dataclass(frozen=True)
class Typography:
    family_kr_body: str = "Pretendard, 'Wanted Sans Std', sans-serif"
    family_en_body: str = "Inter, -apple-system, 'Segoe UI', sans-serif"
    family_mono: str = "'JetBrains Mono', Consolas, monospace"
    family_serif_num: str = "'Source Serif 4', Georgia, serif"
    size_mono_label: int = 10
    size_mono_body: int = 11
    size_label: int = 12
    size_body: int = 13
    size_body_loose: int = 14
    size_number_large: int = 20
    size_number_hero: int = 28
    weight_regular: int = 400
    weight_medium: int = 500
    weight_semibold: int = 600
    line_tight: float = 1.2
    line_base: float = 1.45
    line_loose: float = 1.6


@dataclass(frozen=True)
class Motion:
    duration_instant_ms: int = 0
    duration_fast_ms: int = 120
    duration_base_ms: int = 200
    duration_slow_ms: int = 320
    duration_long_ms: int = 480
    easing_standard: str = "cubic-bezier(0.2, 0.0, 0.0, 1.0)"
    easing_emphasized: str = "cubic-bezier(0.2, 0.0, 0.0, 1.2)"
    easing_decelerate: str = "cubic-bezier(0.0, 0.0, 0.2, 1.0)"
    easing_accelerate: str = "cubic-bezier(0.4, 0.0, 1.0, 1.0)"


@dataclass(frozen=True)
class Opacity:
    hover_bg: float = 0.08
    selected_bg: float = 0.12
    pressed_bg: float = 0.16
    disabled: float = 0.38
    overlay_modal: float = 0.5
    overlay_popover: float = 0.0
    banner_shortcut: float = 0.92


# Carbon 14-class categorical (SBT 14 zone 매핑)
CHART_PALETTE_14: tuple[str, ...] = (
    "#6929C4", "#1192E8", "#005D5D", "#9F1853", "#FA4D56",
    "#570408", "#198038", "#002D9C", "#EE538B", "#B28600",
    "#009D9A", "#012749", "#8A3800", "#A56EFF",
)


@dataclass(frozen=True)
class Tokens:
    palette: Palette
    sizes: Sizes = field(default_factory=Sizes)
    space: Space = field(default_factory=Space)
    type: Typography = field(default_factory=Typography)
    motion: Motion = field(default_factory=Motion)
    opacity: Opacity = field(default_factory=Opacity)
    chart_14: tuple[str, ...] = CHART_PALETTE_14


def make_tokens(palette: PaletteName = "subaqua_pro") -> Tokens:
    if palette not in PALETTES:
        raise ValueError(f"Unknown palette: {palette}. Available: {list(PALETTES)}")
    return Tokens(palette=PALETTES[palette])


def build_qss(tokens: Tokens) -> str:
    """최소 QSS 생성 — Week 20 D1 스모크용. 세부 위젯 QSS 는 Day 4+ 확장."""
    p = tokens.palette
    s = tokens.sizes
    t = tokens.type
    return f"""
    QMainWindow, QWidget {{
        background-color: {p.bg_base};
        color: {p.text_primary};
        font-family: {t.family_kr_body};
        font-size: {t.size_body}px;
    }}
    QFrame#Surface {{
        background-color: {p.bg_surface};
        border: {s.border_default}px solid {p.border_subtle};
        border-radius: {s.radius_md}px;
    }}
    QLabel {{
        background: transparent;
        color: {p.text_primary};
    }}
    QLabel[role="secondary"] {{
        color: {p.text_secondary};
        font-size: {t.size_label}px;
    }}
    QPushButton {{
        background-color: {p.bg_elevated};
        color: {p.text_primary};
        border: {s.border_default}px solid {p.border_subtle};
        border-radius: {s.radius_sm}px;
        padding: {tokens.space.x2}px {tokens.space.x4}px;
    }}
    QPushButton:hover {{
        background-color: {p.accent_muted};
        color: {p.bg_base};
    }}
    QPushButton:focus {{
        outline: {s.focus_outline}px solid {p.accent_primary};
        outline-offset: {s.focus_offset}px;
    }}
    QStatusBar {{
        background-color: {p.bg_surface};
        color: {p.text_secondary};
        border-top: {s.border_default}px solid {p.border_subtle};
    }}
    """


__all__ = [
    "Palette",
    "PaletteName",
    "PALETTES",
    "SUBAQUA_PRO",
    "MINIMAL_GRAPHITE",
    "KOREAN_EARTH",
    "Sizes",
    "Space",
    "Typography",
    "Motion",
    "Opacity",
    "Tokens",
    "CHART_PALETTE_14",
    "make_tokens",
    "build_qss",
]
