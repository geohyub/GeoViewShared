"""
GeoView Brand Colors
====================
**Single Source of Truth** for all GeoView software color tokens.

Used by:
- Desktop apps (CustomTkinter): import directly
- Web apps (Flask): synced to gv-theme.css via generate_css_variables()
- Reports (matplotlib): via qc/common/plot_style.py
- Documents (openpyxl/python-docx): via reporting/design_system.py

Color System:
- Primary navy (#1E3A5F) = brand identity
- Semantic status = green/orange/red for PASS/WARN/FAIL
- Dark cinematic theme for web dashboards
- Light professional theme for desktop apps

Copyright (c) 2025-2026 Geoview Co., Ltd.
"""

# --- Primary Palette ---
PRIMARY = "#1E3A5F"               # Deep navy (brand primary)
PRIMARY_LIGHT = "#2D5F8A"         # Medium blue
PRIMARY_DARK = "#0F2440"          # Dark navy
ACCENT = "#38A169"                # Teal green (accent/success)
ACCENT_WARM = "#ED8936"           # Warm orange (secondary accent)

# --- Semantic Status Colors (QC-wide standard) ---
# Desktop (CTk) uses these for backgrounds/badges.
# Web (CSS) uses --gv-green/--gv-orange/--gv-red which are web-specific vibrant variants.
STATUS_PASS = "#38A169"           # Green — PASS / Excellent (desktop)
STATUS_WARN = "#ED8936"           # Orange — WARNING / Acceptable (desktop)
STATUS_FAIL = "#E53E3E"           # Red — FAIL / Poor (desktop)
STATUS_INFO = "#3182CE"           # Blue — Info / Good
STATUS_NA = "#718096"             # Gray — N/A / No data

# Web-specific vibrant status (matches gv-theme.css Tailwind palette)
WEB_STATUS_PASS = "#10B981"       # Emerald-500 (web)
WEB_STATUS_WARN = "#F59E0B"       # Amber-500 (web)
WEB_STATUS_FAIL = "#EF4444"       # Red-500 (web)

# --- Grade Colors (shared desktop + reports) ---
GRADE_A = "#38A169"               # Green — Excellent
GRADE_B = "#3182CE"               # Blue — Good
GRADE_C = "#ED8936"               # Orange — Acceptable
GRADE_D = "#E53E3E"               # Red — Poor
GRADE_F = "#718096"               # Gray — Fail

# --- Web Accent Colors (cinematic dark theme) ---
WEB_BLUE = "#3B82F6"              # Interactive elements
WEB_CYAN = "#06B6D4"              # Highlights, links
WEB_PURPLE = "#8B5CF6"            # Secondary accents

# --- Surface / Background ---
SURFACE = "#F7FAFC"               # Cool off-white
BG = "#FFFFFF"                    # Pure white
BG_DARK = "#1A202C"               # Dark mode background
CHART_BG = "#F7FAFC"              # Chart background
FOOTER_BG = "#EDF2F7"             # Footer/status bar
SECTION_BG = "#EDF2F7"            # Light section background

# --- Input / Result Fields ---
INPUT_BG = "#FEF9E7"              # Warm cream
INPUT_FG = "#1A202C"              # Dark text
RESULT_BG = "#E8F5E9"             # Soft sage green

# --- Status Indicators ---
GOOD = "#C8E6C9"                  # Pass / normal
WARN = "#FFE0B2"                  # Warning
DANGER = "#FFCDD2"                # Fail / critical
HIGHLIGHT = "#FFF9C4"             # Yellow highlight

# --- Text ---
TEXT_PRIMARY = "#1A202C"          # Near-black
TEXT_SECONDARY = "#4A5568"        # Medium gray
TEXT_MUTED = "#A0AEC0"            # Light gray
TEXT_WARNING = "#E53E3E"          # Red
TEXT_GOOD = "#2E7D32"             # Green
TEXT_ON_PRIMARY = "#FFFFFF"       # White on dark bg

# --- Table / Treeview ---
TABLE_HEADER_BG = PRIMARY
TABLE_HEADER_FG = "#FFFFFF"
TABLE_ROW_ODD = "#FFFFFF"
TABLE_ROW_EVEN = "#F0F4F8"
TABLE_SELECTED_BG = PRIMARY_LIGHT
TABLE_SELECTED_FG = "#FFFFFF"
TABLE_BORDER = "#CBD5E0"

# --- Chart Colors (8-color palette) ---
CHART_PALETTE = [
    "#2D5F8A",  # Blue (primary)
    "#38A169",  # Green (accent)
    "#E05252",  # Red (softer)
    "#ED8936",  # Orange (warm)
    "#7C5DC7",  # Purple
    "#D97706",  # Amber
    "#0891B2",  # Teal
    "#6D5A8F",  # Muted violet
]

# Colorblind-safe palette (Deuteranopia/Protanopia friendly)
CHART_PALETTE_COLORBLIND = [
    "#0077BB",  # Blue
    "#33BBEE",  # Cyan
    "#009988",  # Teal
    "#EE7733",  # Orange
    "#CC3311",  # Red
    "#EE3377",  # Magenta
    "#BBBBBB",  # Grey
    "#332288",  # Indigo
]

# --- Dark Theme Overrides ---
DARK_BG = "#1A202C"
DARK_SURFACE = "#2D3748"
DARK_TEXT = "#E2E8F0"
DARK_TEXT_SECONDARY = "#A0AEC0"
DARK_TEXT_MUTED = "#718096"
DARK_TEXT_GOOD = "#68D391"
DARK_TEXT_WARNING = "#FC8181"
DARK_INPUT_BG = "#2D3748"
DARK_INPUT_FG = "#E2E8F0"
DARK_SECTION_BG = "#2D3748"
DARK_BORDER = "#4A5568"
DARK_CHART_BG = "#2D3748"
DARK_FOOTER_BG = "#1A202C"
DARK_RESULT_BG = "#2D4A3E"
DARK_GOOD = "#2D4A3E"
DARK_WARN = "#4A3B2D"
DARK_DANGER = "#4A2D2D"
DARK_TABLE_ROW_ODD = "#2D3748"
DARK_TABLE_ROW_EVEN = "#1A202C"

# --- Badge / Accent ---
BADGE_BG = PRIMARY_LIGHT
INVALID = "#FED7D7"

# --- Aliases ---
TEXT = TEXT_PRIMARY  # Shorthand alias

# --- Version badge ---
VERSION_BADGE_BG = PRIMARY_LIGHT
VERSION_BADGE_FG = TEXT_ON_PRIMARY


# --- Web Dark Theme (cinematic dashboard) ---
# Maps to CSS custom properties in gv-theme.css
WEB_DARK = {
    # Surfaces (darkest → lightest)
    "bg":       "#060A10",
    "bg_alt":   "#0A0F18",
    "dark":     "#0D1420",
    "navy":     "#111927",
    "slate":    "#192132",
    "surface":  "#1E293B",
    # Accents
    "blue":     WEB_BLUE,
    "cyan":     WEB_CYAN,
    "green":    WEB_STATUS_PASS,
    "orange":   WEB_STATUS_WARN,
    "red":      WEB_STATUS_FAIL,
    "purple":   WEB_PURPLE,
    # Text
    "text":         "#E2E8F0",
    "text_bright":  "#F8FAFC",
    "muted":        "#64748B",
    "dim":          "#475569",
    # Borders
    "border":   "rgba(255,255,255,0.06)",
    "border_h": "rgba(255,255,255,0.12)",
}

# --- Log Console Colors (dark terminal) ---
LOG_BG = "#0F172A"
LOG_FG = "#CBD5E1"
LOG_STEP = "#60A5FA"
LOG_PASS = "#34D399"
LOG_FAIL = "#F87171"
LOG_WARN = "#FBBF24"
LOG_HEADER = "#818CF8"
LOG_DIM = "#475569"


# ---------------------------------------------------------------------------
# CSS Variable Generator (Python → gv-theme.css sync)
# ---------------------------------------------------------------------------

def generate_css_variables() -> str:
    """Generate CSS custom properties from Python color tokens.

    Returns a :root { ... } block that can be injected into gv-theme.css
    or used in a <style> tag.

    Usage:
        css = generate_css_variables()
        Path("gv-theme-tokens.css").write_text(css)
    """
    d = WEB_DARK
    lines = [":root {"]
    lines.append(f"    /* Surface Colors */")
    for key in ("bg", "bg_alt", "dark", "navy", "slate", "surface"):
        lines.append(f"    --gv-{key.replace('_', '-')}: {d[key]};")
    lines.append(f"    /* Accent Colors */")
    for key in ("blue", "cyan", "green", "orange", "red", "purple"):
        lines.append(f"    --gv-{key}: {d[key]};")
        # Dim variants (12% opacity)
        hex_val = d[key].lstrip("#")
        r, g, b = int(hex_val[:2], 16), int(hex_val[2:4], 16), int(hex_val[4:6], 16)
        lines.append(f"    --gv-{key}-dim: rgba({r},{g},{b},0.12);")
    lines.append(f"    /* Text */")
    for key in ("text", "text_bright", "muted", "dim"):
        css_key = key.replace("_", "-")
        lines.append(f"    --gv-{css_key}: {d[key]};")
    lines.append(f"    /* Borders */")
    lines.append(f"    --gv-border: {d['border']};")
    lines.append(f"    --gv-border-h: {d['border_h']};")
    lines.append("}")
    return "\n".join(lines)
