"""
Activity Log Widget — Terminal-style colored log output.

Replaces plain CTkTextbox with a structured log that supports
colored entries by level (info, success, warning, error, step).

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


class ActivityLog(ctk.CTkFrame):
    """Terminal-style activity log with colored entries."""

    def __init__(self, parent, height: int = 300, max_lines: int = 500, **kwargs):
        kwargs.setdefault("corner_radius", 8)
        kwargs.setdefault("fg_color", (colors.LOG_BG, colors.LOG_BG))
        super().__init__(parent, **kwargs)

        self._max_lines = max_lines
        self._line_count = 0

        self._textbox = ctk.CTkTextbox(
            self, font=(MONO, 11), height=height,
            fg_color=(colors.LOG_BG, colors.LOG_BG),
            text_color=(colors.LOG_FG, colors.LOG_FG),
            scrollbar_button_color=(colors.DARK_BORDER, colors.DARK_BORDER),
            corner_radius=0,
        )
        self._textbox.pack(fill="both", expand=True, padx=2, pady=2)
        self._textbox.configure(state="disabled")

    def _append(self, text: str, tag: str = ""):
        """Append a line. MUST be called from the Tk main thread.

        When calling from a worker thread, use:
            root.after(0, lambda: log.info("message"))
        """
        self._textbox.configure(state="normal")
        ts = datetime.now().strftime("%H:%M:%S")
        self._textbox.insert("end", f"[{ts}] {text}\n")
        self._line_count += 1

        # Trim if too many lines
        if self._line_count > self._max_lines:
            self._textbox.delete("1.0", "2.0")
            self._line_count -= 1

        self._textbox.see("end")
        self._textbox.configure(state="disabled")

    def info(self, text: str):
        self._append(f"\u2022 {text}")

    def success(self, text: str):
        self._append(f"\u2713 {text}")

    def warn(self, text: str):
        self._append(f"\u26a0 {text}")

    def error(self, text: str):
        self._append(f"\u2717 {text}")

    def step(self, text: str):
        self._append(f"\u25b6 {text}")

    def header(self, text: str):
        self._append(f"{'='*40}")
        self._append(f"  {text}")
        self._append(f"{'='*40}")

    def clear(self):
        """Clear all log entries."""
        self._textbox.configure(state="normal")
        self._textbox.delete("1.0", "end")
        self._line_count = 0
        self._textbox.configure(state="disabled")

    def get_text(self) -> str:
        """Return all log text."""
        return self._textbox.get("1.0", "end")
