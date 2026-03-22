"""
Activity Log Widget — Terminal-style colored log output.

Replaces plain CTkTextbox with a structured log that supports
colored entries by level (info, success, warning, error, step).

Features:
- Colored dot indicators per log level
- Monospace timestamps for alignment
- Compact display with auto-scroll
- Thread-safe via root.after()

Usage:
    log = ActivityLog(parent, height=300)
    log.pack(fill="both", expand=True)
    log.info("분석 시작...")
    log.success("파싱 완료: 1,234 records")
    log.warn("노이즈 수준 높음")
    log.error("파일 읽기 실패")
    log.step("Stage 3/6: 스파이크 탐지")

Copyright (c) 2025-2026 Geoview Co., Ltd.
"""

from __future__ import annotations

from datetime import datetime

import customtkinter as ctk
from ..styles import colors
from ..styles.fonts import MONO


# Colored dot indicators for each log level
_LEVEL_DOTS = {
    "info":    "\u25cf",  # ● blue
    "success": "\u25cf",  # ● green
    "warn":    "\u25cf",  # ● yellow
    "error":   "\u25cf",  # ● red
    "step":    "\u25b6",  # ▶ blue
    "header":  "\u2550",  # ═ purple
}


class ActivityLog(ctk.CTkFrame):
    """Terminal-style activity log with colored dot indicators."""

    def __init__(self, parent, height: int = 300, max_lines: int = 500, **kwargs):
        kwargs.setdefault("corner_radius", 8)
        kwargs.setdefault("fg_color", (colors.LOG_BG, colors.LOG_BG))
        super().__init__(parent, **kwargs)

        self._max_lines = max_lines
        self._line_count = 0

        # Slightly smaller font for compact display
        self._textbox = ctk.CTkTextbox(
            self, font=(MONO, 10), height=height,
            fg_color=(colors.LOG_BG, colors.LOG_BG),
            text_color=(colors.LOG_FG, colors.LOG_FG),
            scrollbar_button_color=(colors.DARK_BORDER, colors.DARK_BORDER),
            corner_radius=0,
        )
        self._textbox.pack(fill="both", expand=True, padx=2, pady=2)
        self._textbox.configure(state="disabled")

    def _append(self, text: str, level: str = "info"):
        """Append a line with colored dot. MUST be called from the Tk main thread.

        When calling from a worker thread, use:
            root.after(0, lambda: log.info("message"))
        """
        self._textbox.configure(state="normal")
        ts = datetime.now().strftime("%H:%M:%S")
        dot = _LEVEL_DOTS.get(level, "\u2022")
        self._textbox.insert("end", f" {dot} [{ts}] {text}\n")
        self._line_count += 1

        # Trim if too many lines
        if self._line_count > self._max_lines:
            self._textbox.delete("1.0", "2.0")
            self._line_count -= 1

        # Auto-scroll to bottom on new entries
        self._textbox.see("end")
        self._textbox.configure(state="disabled")

    def info(self, text: str):
        self._append(text, "info")

    def success(self, text: str):
        self._append(text, "success")

    def warn(self, text: str):
        self._append(text, "warn")

    def error(self, text: str):
        self._append(text, "error")

    def step(self, text: str):
        self._append(text, "step")

    def header(self, text: str):
        self._append("\u2550" * 38, "header")
        self._append(f"  {text}", "header")
        self._append("\u2550" * 38, "header")

    def clear(self):
        """Clear all log entries."""
        self._textbox.configure(state="normal")
        self._textbox.delete("1.0", "end")
        self._line_count = 0
        self._textbox.configure(state="disabled")

    def get_text(self) -> str:
        """Return all log text."""
        return self._textbox.get("1.0", "end")
