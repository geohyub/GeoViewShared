"""
KPI Card Widget — Professional metric display card.

Shows a key performance indicator with:
- Colored left accent bar
- Title (muted) + large value + optional unit
- Optional trend indicator (up/down/flat arrow)
- Dark/light theme support

Usage:
    card = KPICard(parent, title="파일", accent_color="#2D5F8A")
    card.pack(side="left", expand=True, fill="x", padx=4)
    card.set_value("42", unit="개", trend="up")

Copyright (c) 2025-2026 Geoview Co., Ltd.
"""

from __future__ import annotations

import customtkinter as ctk
from ..styles import colors
from ..styles.fonts import BASE


_TREND_ICONS = {"up": "\u2191", "down": "\u2193", "flat": "\u2192"}  # ↑ ↓ →
_TREND_COLORS = {"up": colors.ACCENT, "down": "#E53E3E", "flat": "#718096"}


class KPICard(ctk.CTkFrame):
    """Professional KPI metric card with accent bar and trend indicator."""

    def __init__(
        self,
        parent,
        title: str = "",
        accent_color: str = colors.PRIMARY_LIGHT,
        initial_value: str = "0",
        unit: str = "",
        **kwargs,
    ):
        kwargs.setdefault("height", 80)
        kwargs.setdefault("corner_radius", 10)
        kwargs.setdefault("fg_color", (colors.SURFACE, colors.DARK_SURFACE))
        kwargs.setdefault("border_width", 1)
        kwargs.setdefault("border_color", (colors.TABLE_BORDER, colors.DARK_BORDER))
        super().__init__(parent, **kwargs)
        self.pack_propagate(False)

        self._accent_color = accent_color

        # Left accent bar
        accent = ctk.CTkFrame(self, width=4, fg_color=accent_color, corner_radius=0)
        accent.pack(side="left", fill="y")

        # Content
        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.pack(side="left", fill="both", expand=True, padx=12, pady=8)

        # Title row
        title_row = ctk.CTkFrame(inner, fg_color="transparent")
        title_row.pack(fill="x")

        self._title_label = ctk.CTkLabel(
            title_row, text=title, font=(BASE, 10),
            text_color=(colors.TEXT_MUTED, colors.DARK_TEXT_MUTED),
            anchor="w",
        )
        self._title_label.pack(side="left")

        self._trend_label = ctk.CTkLabel(
            title_row, text="", font=(BASE, 12),
            text_color="#718096", anchor="e",
        )
        self._trend_label.pack(side="right")

        # Value row
        val_row = ctk.CTkFrame(inner, fg_color="transparent")
        val_row.pack(fill="x", pady=(2, 0))

        self._value_label = ctk.CTkLabel(
            val_row, text=initial_value, font=(BASE, 22, "bold"),
            text_color=(colors.TEXT_PRIMARY, colors.DARK_TEXT),
            anchor="w",
        )
        self._value_label.pack(side="left")

        self._unit_label = ctk.CTkLabel(
            val_row, text=f" {unit}" if unit else "", font=(BASE, 11),
            text_color=(colors.TEXT_MUTED, colors.DARK_TEXT_MUTED),
            anchor="w",
        )
        self._unit_label.pack(side="left", padx=(4, 0))

    def set_value(self, value: str, unit: str = "", trend: str = ""):
        """Update displayed value, optional unit and trend."""
        self._value_label.configure(text=value)
        if unit:
            self._unit_label.configure(text=f" {unit}")
        if trend in _TREND_ICONS:
            self._trend_label.configure(
                text=_TREND_ICONS[trend],
                text_color=_TREND_COLORS[trend],
            )
        elif trend == "":
            self._trend_label.configure(text="")

    def set_title(self, title: str):
        self._title_label.configure(text=title)
