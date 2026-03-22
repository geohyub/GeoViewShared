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


_TREND_ICONS = {"up": "\u25b2", "down": "\u25bc", "flat": "\u25ba"}  # ▲ ▼ ►
_TREND_COLORS = {"up": "#38A169", "down": "#E53E3E", "flat": "#718096"}


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
        kwargs.setdefault("height", 88)
        kwargs.setdefault("corner_radius", 10)
        kwargs.setdefault("fg_color", (colors.SURFACE, colors.DARK_SURFACE))
        kwargs.setdefault("border_width", 1)
        kwargs.setdefault("border_color", (colors.TABLE_BORDER, colors.DARK_BORDER))
        super().__init__(parent, **kwargs)
        self.pack_propagate(False)

        self._accent_color = accent_color
        self._base_fg = kwargs.get("fg_color", (colors.SURFACE, colors.DARK_SURFACE))

        # Top accent bar (3px gradient-like stripe)
        top_accent = ctk.CTkFrame(
            self, height=3, fg_color=accent_color, corner_radius=0,
        )
        top_accent.pack(fill="x", side="top")

        # Left accent bar
        body_wrap = ctk.CTkFrame(self, fg_color="transparent")
        body_wrap.pack(fill="both", expand=True)

        accent = ctk.CTkFrame(body_wrap, width=4, fg_color=accent_color, corner_radius=0)
        accent.pack(side="left", fill="y")

        # Content
        inner = ctk.CTkFrame(body_wrap, fg_color="transparent")
        inner.pack(side="left", fill="both", expand=True, padx=12, pady=8)

        # Title row
        title_row = ctk.CTkFrame(inner, fg_color="transparent")
        title_row.pack(fill="x")

        self._title_label = ctk.CTkLabel(
            title_row, text=title.upper(), font=(BASE, 9, "bold"),
            text_color=(colors.TEXT_MUTED, colors.DARK_TEXT_MUTED),
            anchor="w",
        )
        self._title_label.pack(side="left")

        self._trend_label = ctk.CTkLabel(
            title_row, text="", font=(BASE, 13, "bold"),
            text_color="#718096", anchor="e",
        )
        self._trend_label.pack(side="right")

        # Value row — larger and bolder
        val_row = ctk.CTkFrame(inner, fg_color="transparent")
        val_row.pack(fill="x", pady=(2, 0))

        self._value_label = ctk.CTkLabel(
            val_row, text=initial_value, font=(BASE, 26, "bold"),
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

        # Hover effect: slight brightness increase
        self.bind("<Enter>", self._on_hover_enter)
        self.bind("<Leave>", self._on_hover_leave)

    def _on_hover_enter(self, event=None):
        """Subtle brightness increase on hover."""
        try:
            self.configure(
                fg_color=(colors.SECTION_BG, "#3A4A5E"),
            )
        except Exception:
            pass

    def _on_hover_leave(self, event=None):
        """Restore original background on hover leave."""
        try:
            self.configure(fg_color=self._base_fg)
        except Exception:
            pass

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
        self._title_label.configure(text=title.upper())
