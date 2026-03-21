"""Pipeline Tracker Widget — Multi-stage QC analysis visualization.

Horizontal node-and-connector pipeline showing progress of QC stages.
Each node can be pending, active (pulsing), done (check), or error (cross).
Supports dark/light themes via geoview_common colors.

Originally from SeismicQC Suite, promoted to geoview_common for
reuse across MagQC, SonarQC, and SeismicQC.

Usage:
    from geoview_common.ctk_widgets.pipeline_tracker import PipelineTracker

    tracker = PipelineTracker(parent, stages=["Parse", "Noise", "Spike", "Score"])
    tracker.pack(fill="x")
    tracker.advance()   # Parse -> active
    tracker.advance()   # Parse -> done, Noise -> active

Copyright (c) 2025-2026 Geoview Co., Ltd.
"""

from __future__ import annotations

import tkinter as tk
import customtkinter as ctk
from ..styles import colors
from ..styles.fonts import BASE

# Node state constants
STATE_PENDING = "pending"
STATE_ACTIVE = "active"
STATE_DONE = "done"
STATE_ERROR = "error"
_VALID_STATES = {STATE_PENDING, STATE_ACTIVE, STATE_DONE, STATE_ERROR}


class PipelineTracker(tk.Canvas):
    """Horizontal pipeline showing QC analysis stages with status.

    Args:
        parent: Parent widget.
        stages: List of stage names. Default empty — set via set_stages().
        height: Canvas height in pixels.

    Public API:
        set_stages(names)   — Replace stage list and reset.
        set_stage(i, state) — Set a specific stage's state.
        advance()           — Mark current done, next active.
        complete()          — Mark all done.
        error_at(i)         — Mark stage i as error.
        reset()             — Reset all to pending.
    """

    def __init__(
        self,
        parent,
        stages: list[str] | None = None,
        height: int = 60,
        **kwargs,
    ):
        self._stages = list(stages or [])
        bg = colors.DARK_SURFACE if self._is_dark() else colors.SURFACE
        super().__init__(
            parent, height=height, bg=bg,
            highlightthickness=0, **kwargs,
        )
        self._n = len(self._stages)
        self._current: int = -1
        self._states: list[str] = [STATE_PENDING] * self._n
        self._pulse_state: bool = False
        self._pulse_after_id: str | None = None

        self.bind("<Configure>", lambda _e: self._draw())

    @staticmethod
    def _is_dark() -> bool:
        try:
            return ctk.get_appearance_mode().lower() == "dark"
        except Exception:
            return True

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def set_stages(self, names: list[str]) -> None:
        """Replace stage list and reset all state."""
        self._stop_pulse()
        self._stages = list(names)
        self._n = len(self._stages)
        self._current = -1
        self._states = [STATE_PENDING] * self._n
        self._draw()

    def set_stage(self, index: int, state: str = STATE_ACTIVE) -> None:
        if not (0 <= index < self._n):
            return
        if state not in _VALID_STATES:
            raise ValueError(f"Invalid state '{state}'")
        self._states[index] = state
        if state == STATE_ACTIVE:
            self._current = index
            self._start_pulse()
        self._draw()

    def advance(self) -> None:
        if 0 <= self._current < self._n:
            self._states[self._current] = STATE_DONE
        self._current += 1
        if self._current < self._n:
            self._states[self._current] = STATE_ACTIVE
            self._start_pulse()
        else:
            self._stop_pulse()
        self._draw()

    def complete(self) -> None:
        self._stop_pulse()
        self._states = [STATE_DONE] * self._n
        self._current = self._n
        self._draw()

    def error_at(self, index: int) -> None:
        if 0 <= index < self._n:
            self._states[index] = STATE_ERROR
            self._stop_pulse()
            self._draw()

    def reset(self) -> None:
        self._stop_pulse()
        self._current = -1
        self._states = [STATE_PENDING] * self._n
        self._draw()

    @property
    def current_index(self) -> int:
        return self._current

    @property
    def stages(self) -> list[str]:
        return list(self._stages)

    @property
    def states(self) -> list[str]:
        return list(self._states)

    # ------------------------------------------------------------------
    # Pulse animation
    # ------------------------------------------------------------------
    def _start_pulse(self) -> None:
        self._stop_pulse()
        self._pulse()

    def _stop_pulse(self) -> None:
        if self._pulse_after_id is not None:
            self.after_cancel(self._pulse_after_id)
            self._pulse_after_id = None

    def _pulse(self) -> None:
        self._pulse_state = not self._pulse_state
        self._draw()
        self._pulse_after_id = self.after(500, self._pulse)

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------
    def _draw(self) -> None:
        self.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()
        if w < 10 or self._n == 0:
            return

        is_dark = self._is_dark()
        bg = colors.DARK_SURFACE if is_dark else colors.SURFACE
        self.configure(bg=bg)

        n = self._n
        margin = 30
        usable_w = w - 2 * margin
        spacing = usable_w / max(n - 1, 1)

        node_r = 10
        cy = h * 0.4

        state_colors = {
            STATE_PENDING: colors.DARK_BORDER if is_dark else colors.TABLE_BORDER,
            STATE_ACTIVE:  colors.PRIMARY_LIGHT,
            STATE_DONE:    colors.ACCENT,
            STATE_ERROR:   "#E53E3E",
        }
        text_color = colors.DARK_TEXT if is_dark else colors.TEXT_PRIMARY
        muted = colors.DARK_TEXT_MUTED if is_dark else colors.TEXT_MUTED

        # Connector lines
        for i in range(n - 1):
            x1 = margin + i * spacing + node_r
            x2 = margin + (i + 1) * spacing - node_r
            line_color = (
                state_colors[STATE_DONE]
                if self._states[i] == STATE_DONE
                else state_colors[STATE_PENDING]
            )
            self.create_line(x1, cy, x2, cy, fill=line_color, width=2)

        # Nodes
        for i in range(n):
            x = margin + i * spacing
            state = self._states[i]
            color = state_colors[state]

            # Pulse ring
            if state == STATE_ACTIVE and self._pulse_state:
                pulse_r = node_r + 4
                self.create_oval(
                    x - pulse_r, cy - pulse_r,
                    x + pulse_r, cy + pulse_r,
                    fill="", outline=color, width=2, dash=(3, 3),
                )

            # Node circle
            self.create_oval(
                x - node_r, cy - node_r,
                x + node_r, cy + node_r,
                fill=color, outline="",
            )

            # Inner indicator
            if state == STATE_DONE:
                self.create_text(x, cy, text="\u2713", font=(BASE, 12, "bold"), fill="white")
            elif state == STATE_ERROR:
                self.create_text(x, cy, text="\u2717", font=(BASE, 12, "bold"), fill="white")
            elif state == STATE_ACTIVE:
                self.create_oval(x - 3, cy - 3, x + 3, cy + 3, fill="white", outline="")

            # Label
            label_color = text_color if state in (STATE_ACTIVE, STATE_DONE) else muted
            self.create_text(
                x, cy + node_r + 12,
                text=self._stages[i],
                font=(BASE, 10),
                fill=label_color,
            )

    def destroy(self) -> None:
        self._stop_pulse()
        super().destroy()
