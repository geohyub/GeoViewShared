"""
Data Table Widget — Pure CTk scrollable data table.

Replaces tkinter.ttk.Treeview and CTkTextbox-based file lists
with a proper scrollable table using CTk widgets only.

Features:
- Column headers with sort indicator
- Alternating row colors
- Row selection (single click)
- Scrollable with mousewheel
- Dark/light theme support
- Click callback

Usage:
    table = DataTable(parent, columns=["파일명", "크기", "상태"])
    table.pack(fill="both", expand=True)
    table.set_data([
        ["test.mag", "1.2 MB", "PASS"],
        ["line2.mag", "0.8 MB", "WARN"],
    ])

Copyright (c) 2025-2026 Geoview Co., Ltd.
"""

from __future__ import annotations

from typing import Callable, Optional

import customtkinter as ctk
from ..styles import colors
from ..styles.fonts import BASE, MONO


class DataTable(ctk.CTkFrame):
    """Pure CTk scrollable data table with headers and row selection."""

    def __init__(
        self,
        parent,
        columns: list[str],
        column_widths: Optional[list[int]] = None,
        on_row_click: Optional[Callable[[int, list[str]], None]] = None,
        row_height: int = 32,
        max_rows: int = 500,
        **kwargs,
    ):
        kwargs.setdefault("corner_radius", 8)
        kwargs.setdefault("fg_color", (colors.SURFACE, colors.DARK_SURFACE))
        kwargs.setdefault("border_width", 1)
        kwargs.setdefault("border_color", (colors.TABLE_BORDER, colors.DARK_BORDER))
        super().__init__(parent, **kwargs)

        self._columns = columns
        self._n_cols = len(columns)
        self._col_widths = column_widths or [None] * self._n_cols
        self._on_row_click = on_row_click
        self._row_height = row_height
        self._max_rows = max_rows
        self._data: list[list[str]] = []
        self._selected_row: int = -1
        self._row_frames: list[ctk.CTkFrame] = []
        self._row_labels: list[list[ctk.CTkLabel]] = []

        self._build()

    def _build(self):
        # Header — slightly darker with bold text
        header = ctk.CTkFrame(
            self, height=38,
            fg_color=(colors.PRIMARY_DARK, colors.PRIMARY_DARK),
            corner_radius=0,
        )
        header.pack(fill="x")
        header.pack_propagate(False)

        for i, col_name in enumerate(self._columns):
            w = self._col_widths[i]
            lbl = ctk.CTkLabel(
                header, text=col_name,
                font=(BASE, 11, "bold"), text_color="white",
                anchor="w",
            )
            if w:
                lbl.pack(side="left", padx=(12 if i == 0 else 6, 6), fill="y")
                lbl.configure(width=w)
            else:
                lbl.pack(side="left", expand=True, fill="both", padx=(12 if i == 0 else 6, 6))

        # Scrollable body
        self._scroll = ctk.CTkScrollableFrame(
            self, fg_color="transparent",
            scrollbar_button_color=(colors.TABLE_BORDER, colors.DARK_BORDER),
        )
        self._scroll.pack(fill="both", expand=True)

        # Empty state
        self._empty_label = ctk.CTkLabel(
            self._scroll, text="\ub370\uc774\ud130 \uc5c6\uc74c",
            font=(BASE, 12), text_color=(colors.TEXT_MUTED, colors.DARK_TEXT_MUTED),
        )
        self._empty_label.pack(pady=20)

    def set_data(self, data: list[list[str]]):
        """Replace all table data."""
        self._data = data[:self._max_rows]
        self._selected_row = -1
        self._rebuild_rows()

    def append_row(self, row: list[str]):
        """Append a single row."""
        if len(self._data) >= self._max_rows:
            return
        self._data.append(row)
        # Hide empty label before adding row (pack_forget is safe even if not mapped)
        self._empty_label.pack_forget()
        self._add_row_widget(len(self._data) - 1, row)

    def clear(self):
        """Remove all data."""
        self._data = []
        self._selected_row = -1
        self._rebuild_rows()

    def get_selected(self) -> Optional[tuple[int, list[str]]]:
        """Return (index, row_data) or None."""
        if 0 <= self._selected_row < len(self._data):
            return (self._selected_row, self._data[self._selected_row])
        return None

    @property
    def row_count(self) -> int:
        return len(self._data)

    def _rebuild_rows(self):
        """Rebuild all row widgets from scratch."""
        for frame in self._row_frames:
            frame.destroy()
        self._row_frames.clear()
        self._row_labels.clear()

        if not self._data:
            if not self._empty_label.winfo_ismapped():
                self._empty_label.pack(pady=20)
            return

        if self._empty_label.winfo_ismapped():
            self._empty_label.pack_forget()

        for idx, row in enumerate(self._data):
            self._add_row_widget(idx, row)

    def _add_row_widget(self, idx: int, row: list[str]):
        """Add a single row widget with hover, border, and zebra striping."""
        is_even = idx % 2 == 0
        bg = (
            (colors.TABLE_ROW_EVEN, colors.DARK_TABLE_ROW_EVEN) if is_even
            else (colors.TABLE_ROW_ODD, colors.DARK_TABLE_ROW_ODD)
        )

        # Row wrapper (includes bottom border line)
        row_wrapper = ctk.CTkFrame(
            self._scroll, fg_color="transparent", corner_radius=0,
        )
        row_wrapper.pack(fill="x", pady=0)

        frame = ctk.CTkFrame(
            row_wrapper, height=self._row_height,
            fg_color=bg, corner_radius=0,
        )
        frame.pack(fill="x")
        frame.pack_propagate(False)
        frame.bind("<Button-1>", lambda e, i=idx: self._select_row(i))

        # Thin bottom border for row separation
        ctk.CTkFrame(
            row_wrapper, height=1,
            fg_color=(colors.TABLE_BORDER, colors.DARK_BORDER),
            corner_radius=0,
        ).pack(fill="x")

        # Store original bg for hover restore
        frame._row_bg = bg

        # Hover highlight (subtle blue tint)
        def on_enter(e, f=frame, i=idx):
            if i != self._selected_row:
                f.configure(fg_color=("#E2ECF5", "#1E2D42"))

        def on_leave(e, f=frame, i=idx):
            if i != self._selected_row:
                f.configure(fg_color=f._row_bg)

        frame.bind("<Enter>", on_enter)
        frame.bind("<Leave>", on_leave)

        labels = []
        for j, cell in enumerate(row[:self._n_cols]):
            w = self._col_widths[j]
            cell_font = (MONO, 11) if j == 0 else (BASE, 11)
            lbl = ctk.CTkLabel(
                frame, text=str(cell),
                font=cell_font,
                text_color=(colors.TEXT_PRIMARY, colors.DARK_TEXT),
                anchor="w",
            )

            if w:
                lbl.pack(side="left", padx=(12 if j == 0 else 6, 6), fill="y")
                lbl.configure(width=w)
            else:
                lbl.pack(side="left", expand=True, fill="both", padx=(12 if j == 0 else 6, 6))

            lbl.bind("<Button-1>", lambda e, i=idx: self._select_row(i))
            # Propagate hover events from labels to parent frame
            lbl.bind("<Enter>", on_enter)
            lbl.bind("<Leave>", on_leave)
            labels.append(lbl)

        self._row_frames.append(frame)
        self._row_labels.append(labels)

    def _select_row(self, idx: int):
        """Handle row selection with clear blue accent."""
        prev = self._selected_row
        _text_default = (colors.TEXT_PRIMARY, colors.DARK_TEXT)

        # Deselect previous — restore both bg and text color
        if 0 <= prev < len(self._row_frames):
            frame = self._row_frames[prev]
            frame.configure(fg_color=frame._row_bg)
            for lbl in self._row_labels[prev]:
                lbl.configure(text_color=_text_default)

        # Select new — clear blue accent
        self._selected_row = idx
        if 0 <= idx < len(self._row_frames):
            self._row_frames[idx].configure(
                fg_color=(colors.PRIMARY_LIGHT, "#2D5F8A")
            )
            for lbl in self._row_labels[idx]:
                lbl.configure(text_color="white")

            if self._on_row_click and 0 <= idx < len(self._data):
                self._on_row_click(idx, self._data[idx])
