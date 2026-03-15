"""
GeoView Font Definitions
========================
Centralized font registry for consistent typography.

Primary font: Pretendard (Korean-optimized modern sans-serif)
Fallback: Segoe UI (Windows), SF Pro Text (macOS), Noto Sans (Linux)

Copyright (c) 2025-2026 Geoview Co., Ltd.
"""

import platform

# ── Font Family Constants ──────────────────────────────────

# Pretendard is set as the primary font for all GeoView apps.
# It provides excellent Korean readability with clean Latin glyphs.
# If Pretendard is not installed, tkinter will fall back silently
# to the next available font in its internal resolution chain.

PRETENDARD = "Pretendard"


def _base_family():
    """Platform-appropriate sans-serif font."""
    system = platform.system()
    if system == "Windows":
        return PRETENDARD          # Pretendard (Korean-optimized)
    elif system == "Darwin":
        return "SF Pro Text"
    return "Noto Sans"


def _mono_family():
    """Platform-appropriate monospace font."""
    system = platform.system()
    if system == "Windows":
        return "Consolas"
    elif system == "Darwin":
        return "SF Mono"
    return "Noto Sans Mono"


BASE = _base_family()
MONO = _mono_family()

# ── Named font tuples (family, size, weight) ───────────────

TITLE = (BASE, 16, "bold")
SECTION = (BASE, 13, "bold")
BODY = (BASE, 12)
INPUT = (BASE, 12)
RESULT = (BASE, 12, "bold")
MONOSPACE = (MONO, 12)
SMALL = (BASE, 11)
HEADER = (BASE, 12, "bold")
TAB_TITLE = (BASE, 15, "bold")
NOTE = (BASE, 11)
TOOLBAR = (BASE, 11)
TOOLTIP = (BASE, 11)
