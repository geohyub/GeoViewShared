"""
GeoView Brand Colors
====================
Unified color palette for all GeoView software.
Based on GeoView_Calculator v2.2 config.py with extensions.
"""

# --- Primary Palette ---
PRIMARY = "#1E3A5F"               # Deep navy (brand primary)
PRIMARY_LIGHT = "#2D5F8A"         # Medium blue
PRIMARY_DARK = "#0F2440"          # Dark navy
ACCENT = "#38A169"                # Teal green (accent/success)
ACCENT_WARM = "#ED8936"           # Warm orange (secondary accent)

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

# --- Chart Colors (5-color palette) ---
CHART_PALETTE = ["#2D5F8A", "#38A169", "#E53E3E", "#ED8936", "#805AD5"]

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
