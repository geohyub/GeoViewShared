"""Score Gauge Widget — Modern QC score card display.

CTkFrame-based metric card showing QC score (0-100) with grade badge,
animated progress bar, and status label. Pure CustomTkinter — seamless
dark/light theming.

Originally from SeismicQC Suite, promoted to geoview_common for
reuse across all QC modules.

Usage:
    from geoview_common.ctk_widgets.score_gauge import ScoreGauge

    gauge = ScoreGauge(parent, size=200)
    gauge.pack()
    gauge.set_score(87.5)

Copyright (c) 2025-2026 Geoview Co., Ltd.
"""

from __future__ import annotations

import customtkinter as ctk
from ..styles import colors
from ..styles.fonts import BASE

# Grade color palettes
GRADE_COLORS = {
    "A": "#38A169", "B": "#3182CE", "C": "#ED8936",
    "D": "#E53E3E", "F": "#718096",
}

_GRADE_THRESHOLDS: list[tuple[float, str, str, str]] = [
    (90, "A", "Excellent", "우수"),
    (80, "B", "Good", "양호"),
    (70, "C", "Acceptable", "보통"),
    (60, "D", "Poor", "미흡"),
    (0, "F", "Fail", "불합격"),
]


class ScoreGauge(ctk.CTkFrame):
    """Modern QC score card widget with animated progress bar.

    Args:
        parent: Parent widget.
        size: Widget size in pixels (width and height).

    Public API:
        set_score(score, grade="", status="")
        reset()
        .score, .grade properties
    """

    def __init__(self, parent, size: int = 200, **kwargs):
        kwargs.pop("bg", None)
        kwargs.pop("highlightthickness", None)
        super().__init__(parent, width=size, height=size, fg_color="transparent", **kwargs)

        self._size = size
        self._score: float = 0.0
        self._display_score: float = 0.0
        self._grade: str = "-"
        self._status: str = "No Data"
        self._anim_id: str | None = None

        self._build_ui()
        self._apply_grade_style("F")

    def _build_ui(self) -> None:
        s = self._size
        score_fs = max(16, int(s * 0.22))
        max_fs = max(10, int(s * 0.09))
        grade_fs = max(14, int(s * 0.14))
        status_fs = max(10, int(s * 0.065))
        bar_h = max(6, int(s * 0.04))
        badge_w = max(36, int(s * 0.22))
        badge_h = max(28, int(s * 0.15))

        self._score_label = ctk.CTkLabel(
            self, text="—", font=(BASE, score_fs, "bold"),
            text_color=(colors.TEXT_PRIMARY, colors.DARK_TEXT),
        )
        self._score_label.pack(pady=(int(s * 0.12), 0))

        self._max_label = ctk.CTkLabel(
            self, text="/ 100", font=(BASE, max_fs),
            text_color=(colors.TEXT_MUTED, colors.DARK_TEXT_MUTED),
        )
        self._max_label.pack(pady=(0, int(s * 0.06)))

        self._bar = ctk.CTkProgressBar(
            self, width=int(s * 0.78), height=bar_h,
            corner_radius=bar_h // 2,
            progress_color=GRADE_COLORS["F"],
            fg_color=(colors.TABLE_BORDER, colors.DARK_BORDER),
        )
        self._bar.set(0)
        self._bar.pack(pady=(0, int(s * 0.08)))

        badge_row = ctk.CTkFrame(self, fg_color="transparent")
        badge_row.pack(pady=(0, int(s * 0.06)))

        self._badge_frame = ctk.CTkFrame(
            badge_row, width=badge_w, height=badge_h,
            corner_radius=badge_h // 2, fg_color=GRADE_COLORS["F"],
        )
        self._badge_frame.pack(side="left", padx=(0, 8))
        self._badge_frame.pack_propagate(False)

        self._grade_label = ctk.CTkLabel(
            self._badge_frame, text="-",
            font=(BASE, grade_fs, "bold"), text_color="#FFFFFF",
        )
        self._grade_label.place(relx=0.5, rely=0.5, anchor="center")

        self._status_label = ctk.CTkLabel(
            badge_row, text="No Data", font=(BASE, status_fs),
            text_color=(colors.TEXT_MUTED, colors.DARK_TEXT_MUTED),
        )
        self._status_label.pack(side="left")

    # -- Public API --

    def set_score(self, score: float, grade: str = "", status: str = "") -> None:
        self._score = max(0.0, min(100.0, float(score)))
        self._grade = grade or self._auto_grade(self._score)
        self._status = status or self._auto_status(self._score)
        self._display_score = 0.0
        self._apply_grade_style(self._grade)
        self._cancel_animation()
        self._animate()

    def reset(self) -> None:
        self._cancel_animation()
        self._score = 0.0
        self._display_score = 0.0
        self._grade = "-"
        self._status = "No Data"
        self._apply_grade_style("F")
        self._update_display()

    @property
    def score(self) -> float:
        return self._score

    @property
    def grade(self) -> str:
        return self._grade

    # -- Internals --

    @staticmethod
    def _auto_grade(score: float) -> str:
        for threshold, letter, _, _ in _GRADE_THRESHOLDS:
            if score >= threshold:
                return letter
        return "F"

    @staticmethod
    def _auto_status(score: float) -> str:
        for threshold, _, label, _ in _GRADE_THRESHOLDS:
            if score >= threshold:
                return label
        return "Fail"

    def _apply_grade_style(self, grade: str) -> None:
        color = GRADE_COLORS.get(grade, GRADE_COLORS["F"])
        self._badge_frame.configure(fg_color=color)
        self._bar.configure(progress_color=color)
        self._score_label.configure(text_color=color)

    def _cancel_animation(self) -> None:
        if self._anim_id is not None:
            self.after_cancel(self._anim_id)
            self._anim_id = None

    def _animate(self) -> None:
        if self._display_score < self._score:
            remaining = self._score - self._display_score
            step = max(0.4, remaining * 0.12)
            self._display_score = min(self._score, self._display_score + step)
            self._update_display()
            self._anim_id = self.after(16, self._animate)
        else:
            self._display_score = self._score
            self._anim_id = None
            self._update_display()

    def _update_display(self) -> None:
        if self._display_score == 0 and self._grade == "-":
            self._score_label.configure(text="—")
        else:
            val = self._display_score
            self._score_label.configure(
                text=f"{int(val)}" if val == int(val) else f"{val:.1f}"
            )
        self._bar.set(self._display_score / 100.0)
        self._grade_label.configure(text=self._grade)
        self._status_label.configure(text=self._status)

    def destroy(self) -> None:
        self._cancel_animation()
        super().destroy()
