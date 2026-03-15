"""
GeoView Themes
==============
Light and dark theme definitions for CustomTkinter apps.
"""

from . import colors


LIGHT_THEME = {
    "bg": colors.BG,
    "surface": colors.SURFACE,
    "primary": colors.PRIMARY,
    "primary_light": colors.PRIMARY_LIGHT,
    "accent": colors.ACCENT,
    "text": colors.TEXT_PRIMARY,
    "text_secondary": colors.TEXT_SECONDARY,
    "text_muted": colors.TEXT_MUTED,
    "input_bg": colors.INPUT_BG,
    "input_fg": colors.INPUT_FG,
    "result_bg": colors.RESULT_BG,
    "section_bg": colors.SECTION_BG,
    "good": colors.GOOD,
    "warn": colors.WARN,
    "danger": colors.DANGER,
    "border": colors.TABLE_BORDER,
}

DARK_THEME = {
    "bg": colors.DARK_BG,
    "surface": colors.DARK_SURFACE,
    "primary": colors.PRIMARY,
    "primary_light": colors.PRIMARY_LIGHT,
    "accent": colors.ACCENT,
    "text": colors.DARK_TEXT,
    "text_secondary": "#A0AEC0",
    "text_muted": "#718096",
    "input_bg": colors.DARK_INPUT_BG,
    "input_fg": colors.DARK_INPUT_FG,
    "result_bg": "#2D3748",
    "section_bg": colors.DARK_SECTION_BG,
    "good": "#276749",
    "warn": "#744210",
    "danger": "#9B2C2C",
    "border": colors.DARK_BORDER,
}

# Font definitions (platform-aware)
FONTS = {
    "title": ("Pretendard", 12, "bold"),
    "section": ("Pretendard", 10, "bold"),
    "body": ("Pretendard", 9),
    "input": ("Pretendard", 9),
    "result": ("Pretendard", 9, "bold"),
    "mono": ("Consolas", 9),
    "small": ("Pretendard", 8),
    "header": ("Pretendard", 9, "bold"),
    "tab_title": ("Pretendard", 12, "bold"),
    "note": ("Pretendard", 8),
    "toolbar": ("Pretendard", 8),
}

# Physical constants used across survey calculators
CONSTANTS = {
    "sound_speed_default": 1500.0,   # m/s in seawater
    "earth_radius": 6371000.0,       # meters (WGS84 mean)
    "prf_cap": 50.0,                 # Max pulse repetition frequency (Hz)
    "two_way_bw_adj": 0.72,          # SSS two-way beamwidth adjustment
    "sidelobe_adj": 1.15,            # SSS sidelobe adjustment
    "knots_to_ms": 0.514444,         # knots → m/s conversion
}
