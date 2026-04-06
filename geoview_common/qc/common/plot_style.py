"""
QC Plot Style — Unified matplotlib styling for all QC reports.
================================================================
Adapted from SonarQC's visualization/style.py with GeoView branding.

Usage:
    from geoview_common.qc.common.plot_style import apply_style, save_figure

    fig, ax = plt.subplots()
    apply_style(ax)
    ax.plot(x, y)
    save_figure(fig, "output.png")

Copyright (c) 2025-2026 Geoview Co., Ltd.
"""

from __future__ import annotations

from typing import Optional

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend for server/report use

import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from pathlib import Path

from ...styles import colors

# ---------------------------------------------------------------------------
# Color constants (from geoview_common colors)
# ---------------------------------------------------------------------------

NAVY = colors.PRIMARY            # #1E3A5F
BLUE = colors.PRIMARY_LIGHT      # #2D5F8A
GREEN = colors.ACCENT            # #38A169
ORANGE = colors.ACCENT_WARM      # #ED8936
RED = "#E53E3E"
GRAY = colors.TEXT_SECONDARY     # #4A5568
LIGHT_GRAY = "#CBD5E0"

# 5-color chart palette
PALETTE = colors.CHART_PALETTE   # ["#2D5F8A", "#38A169", "#E53E3E", "#ED8936", "#805AD5"]

# Status colors for QC results
STATUS_COLORS = {
    "PASS": GREEN,
    "WARN": ORANGE,
    "FAIL": RED,
    "N/A": GRAY,
    "EXCELLENT": GREEN,
    "GOOD": BLUE,
    "ACCEPTABLE": ORANGE,
    "POOR": RED,
}

# Grade colors
GRADE_COLORS = {
    "A": GREEN,
    "B": BLUE,
    "C": ORANGE,
    "D": RED,
    "F": GRAY,
}

# Coverage heatmap colors (from SonarQC)
COVERAGE_COLORS = {
    "gap": "#ECEFF1",
    "100": "#FFF176",
    "200": "#66BB6A",
    "300+": "#42A5F5",
}


# ---------------------------------------------------------------------------
# Font configuration
# ---------------------------------------------------------------------------

def _resolve_font() -> str:
    """Find best available font for Korean+English."""
    preferred = ["Pretendard", "Pretendard Variable", "Noto Sans KR",
                 "Malgun Gothic", "Segoe UI", "DejaVu Sans"]
    available = {f.name for f in fm.fontManager.ttflist}
    for font in preferred:
        if font in available:
            return font
    return "sans-serif"


FONT_FAMILY = _resolve_font()


# ---------------------------------------------------------------------------
# Apply GeoView style to axes
# ---------------------------------------------------------------------------

def apply_style(
    ax: plt.Axes,
    title: str = "",
    xlabel: str = "",
    ylabel: str = "",
    dark: bool = False,
    grid: bool = True,
) -> None:
    """Apply GeoView professional style to a matplotlib Axes.

    Args:
        ax: Target axes.
        title: Plot title.
        xlabel/ylabel: Axis labels.
        dark: Use dark theme (for desktop embedding).
        grid: Show grid lines.
    """
    if dark:
        bg = colors.DARK_BG
        text = colors.DARK_TEXT
        grid_color = colors.DARK_BORDER
    else:
        bg = "#FFFFFF"
        text = colors.TEXT_PRIMARY
        grid_color = "#E2E8F0"

    ax.set_facecolor(bg)
    ax.figure.set_facecolor(bg)

    # Title
    if title:
        ax.set_title(title, fontfamily=FONT_FAMILY, fontsize=12,
                      fontweight="bold", color=NAVY if not dark else "#E2E8F0",
                      pad=10)

    # Axis labels
    label_kw = dict(fontfamily=FONT_FAMILY, fontsize=10, color=text)
    if xlabel:
        ax.set_xlabel(xlabel, **label_kw)
    if ylabel:
        ax.set_ylabel(ylabel, **label_kw)

    # Tick styling
    ax.tick_params(colors=text, labelsize=9)
    for spine in ax.spines.values():
        spine.set_color(grid_color)
        spine.set_linewidth(0.5)

    # Remove top/right spines (clean style)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # Grid
    if grid:
        ax.grid(True, alpha=0.25, color=grid_color, linewidth=0.5, linestyle="--")
    else:
        ax.grid(False)


def apply_rcparams(dark: bool = False) -> None:
    """Set global matplotlib rcParams for GeoView style."""
    plt.rcParams.update({
        "font.family": FONT_FAMILY,
        "font.size": 10,
        "axes.titlesize": 12,
        "axes.labelsize": 10,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "legend.fontsize": 9,
        "figure.titlesize": 14,
        "figure.dpi": 150,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.1,
        "axes.prop_cycle": plt.cycler(color=PALETTE),
    })

    if dark:
        plt.rcParams.update({
            "figure.facecolor": colors.DARK_BG,
            "axes.facecolor": colors.DARK_SURFACE,
            "text.color": colors.DARK_TEXT,
            "axes.labelcolor": colors.DARK_TEXT,
            "xtick.color": colors.DARK_TEXT,
            "ytick.color": colors.DARK_TEXT,
        })


def save_figure(
    fig: plt.Figure,
    path: str | Path,
    dpi: int = 300,
    transparent: bool = False,
) -> Path:
    """Save figure with GeoView defaults.

    Returns:
        Path to saved file.
    """
    path = Path(path)
    fig.savefig(
        path,
        dpi=dpi,
        bbox_inches="tight",
        pad_inches=0.1,
        transparent=transparent,
        facecolor=fig.get_facecolor(),
        edgecolor="none",
    )
    plt.close(fig)
    return path


def status_color(status: str) -> str:
    """Get color for a QC status string."""
    return STATUS_COLORS.get(status, GRAY)


def grade_color(grade: str) -> str:
    """Get color for a grade letter."""
    return GRADE_COLORS.get(grade, GRAY)


def get_figure_size(aspect: str = "wide") -> tuple[float, float]:
    """차트 크기 반환 (inches). wide=(14, 4.5), square=(8, 8), tall=(8, 12)."""
    sizes = {"wide": (14, 4.5), "square": (8, 8), "tall": (8, 12), "compact": (10, 3.5)}
    return sizes.get(aspect, sizes["wide"])

def add_toolbar(canvas, parent=None):
    """Matplotlib FigureCanvas에 NavigationToolbar 부착."""
    from matplotlib.backends.backend_qtagg import NavigationToolbar2QT
    toolbar = NavigationToolbar2QT(canvas, parent)
    return toolbar
