"""
GeoView Base Application v3.0
==============================
Professional CustomTkinter application frame with:
- Collapsible sidebar navigation with icons
- Enhanced 56px navy header with breadcrumb
- Notification badge area
- Status bar with progress indicator
- Dark/Light theme toggle (Korean labels)
- Keyboard shortcuts (Ctrl+Q quit, Ctrl+T theme, Ctrl+B sidebar)
- Centered window on startup

Usage:
    from geoview_common.ctk_widgets.base_app import GeoViewApp

    class MyApp(GeoViewApp):
        APP_TITLE = "MagQC"
        APP_VERSION = "2.0"
        APP_SUBTITLE = "자력 데이터 QC"

        def get_nav_items(self):
            return [
                ("home", "홈", "H"),
                ("analysis", "분석", "A"),
                ("upload", "업로드", "U"),
                ("settings", "설정", "S"),
            ]

        def build_page(self, page_id, parent):
            ...

    if __name__ == "__main__":
        app = MyApp()
        app.run()

Copyright (c) 2025-2026 Geoview Co., Ltd.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    import customtkinter as ctk
    HAS_CTK = True
except ImportError:
    HAS_CTK = False

from ..styles import colors
from ..styles.fonts import BASE


# ── Sidebar icon glyphs ──────────────────────────────────────
# Simple single-char icons for sidebar nav items
ICONS = {
    "home": "\u2302",       # ⌂
    "analysis": "\u2261",   # ≡
    "upload": "\u2191",     # ↑
    "settings": "\u2699",   # ⚙
    "report": "\u2637",     # ☷
    "batch": "\u229e",      # ⊞
    "viz": "\u25ce",        # ◎
    "mag": "\u2609",        # ☉
    "sonar": "\u2307",      # ⌇
    "seismic": "\u2248",    # ≈
    "editor": "\u270e",     # ✎
    "export": "\u21e9",     # ⇩
    "module": "\u25a3",     # ▣
    "web": "\u2301",        # ⌁
}

_SIDEBAR_W_OPEN = 180
_SIDEBAR_W_CLOSED = 52
_HEADER_H = 56
_STATUS_H = 30


class GeoViewApp:
    """Professional base class for GeoView desktop applications (v3).

    Subclasses should override:
        get_nav_items() -> list of (id, label, icon_key_or_char)
        build_page(page_id, parent) -> build UI in parent frame
    OR legacy:
        build_content(parent) -> build all UI in content area (no sidebar)
    """

    APP_TITLE = "GeoView"
    APP_VERSION = "1.0"
    APP_SUBTITLE = ""
    APP_COPYRIGHT = "\u00a9 2025-2026 Geoview Co., Ltd."
    WINDOW_SIZE = "1400x900"
    WINDOW_MIN_SIZE = (1200, 700)

    # Sidebar config (set False to disable sidebar)
    USE_SIDEBAR = True
    SIDEBAR_DEFAULT_OPEN = True

    def __init__(self):
        if not HAS_CTK:
            raise ImportError(
                "customtkinter is required: pip install customtkinter"
            )

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.root = ctk.CTk()
        self.root.title(f"{self.APP_TITLE} v{self.APP_VERSION}")
        self.root.geometry(self.WINDOW_SIZE)
        self.root.minsize(*self.WINDOW_MIN_SIZE)

        self._dark_mode = True
        self._sidebar_open = self.SIDEBAR_DEFAULT_OPEN
        self._current_page: str = ""
        self._nav_buttons: dict[str, ctk.CTkButton] = {}
        self._nav_labels: dict[str, ctk.CTkLabel] = {}
        self._pages: dict[str, ctk.CTkFrame] = {}
        self._notification_count = 0
        self._clock_after_id: str | None = None
        # Cache nav items once to avoid repeated virtual calls
        self._cached_nav_items: list[tuple[str, str, str]] = []

        self._build_layout()

        # Center window
        self.root.update_idletasks()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        x = max(0, (self.root.winfo_screenwidth() - w) // 2)
        y = max(0, (self.root.winfo_screenheight() - h) // 2)
        self.root.geometry(f"+{x}+{y}")

        # Keyboard shortcuts
        self.root.bind_all("<Control-q>", lambda e: self._quit())
        self.root.bind_all("<Control-t>", lambda e: self._toggle_theme())
        if self.USE_SIDEBAR:
            self.root.bind_all("<Control-b>", lambda e: self._toggle_sidebar())

    # ==================================================================
    # LAYOUT BUILD
    # ==================================================================

    def _build_layout(self):
        """Build the complete professional layout."""
        # ── Header bar ──
        self._build_header()

        # ── Body (sidebar + content) ──
        body = ctk.CTkFrame(self.root, fg_color="transparent")
        body.pack(fill="both", expand=True)
        self._body = body

        nav_items = self.get_nav_items() if self.USE_SIDEBAR else []
        self._cached_nav_items = list(nav_items)

        if self.USE_SIDEBAR and nav_items:
            self._build_sidebar(body, nav_items)
            self._content_area = ctk.CTkFrame(body, fg_color="transparent")
            self._content_area.pack(side="left", fill="both", expand=True)

            # Build pages
            for item_id, label, icon in nav_items:
                page = ctk.CTkFrame(self._content_area, fg_color="transparent")
                self._pages[item_id] = page
                self.build_page(item_id, page)

            # Show first page
            if nav_items:
                self.navigate(nav_items[0][0])
        else:
            # Legacy mode — no sidebar, just content area
            self.content = ctk.CTkFrame(body, fg_color="transparent")
            self.content.pack(fill="both", expand=True)
            self.build_content(self.content)

        # ── Status bar ──
        self._build_statusbar()

    def _build_header(self):
        """Build the enhanced 56px navy header."""
        self.header = ctk.CTkFrame(
            self.root, height=_HEADER_H,
            fg_color=colors.PRIMARY, corner_radius=0,
        )
        self.header.pack(fill="x")
        self.header.pack_propagate(False)

        # Left: Sidebar toggle + Icon + Title
        left = ctk.CTkFrame(self.header, fg_color="transparent")
        left.pack(side="left", padx=(8, 0))

        if self.USE_SIDEBAR:
            self._sidebar_toggle_btn = ctk.CTkButton(
                left, text="\u2630", width=36, height=36,  # ☰
                font=(BASE, 16), fg_color="transparent",
                hover_color=colors.PRIMARY_LIGHT,
                text_color="white", corner_radius=8,
                command=self._toggle_sidebar,
            )
            self._sidebar_toggle_btn.pack(side="left", padx=(0, 4))

        # App icon (rounded colored dot with letter)
        icon_frame = ctk.CTkFrame(
            left, width=34, height=34,
            fg_color=colors.ACCENT, corner_radius=17,
        )
        icon_frame.pack(side="left", padx=(4, 8))
        icon_frame.pack_propagate(False)
        ctk.CTkLabel(
            icon_frame, text=self.APP_TITLE[0] if self.APP_TITLE else "G",
            font=(BASE, 14, "bold"), text_color="white",
        ).place(relx=0.5, rely=0.5, anchor="center")

        # Title + version badge
        title_frame = ctk.CTkFrame(left, fg_color="transparent")
        title_frame.pack(side="left")

        ctk.CTkLabel(
            title_frame, text=self.APP_TITLE,
            font=(BASE, 18, "bold"), text_color="white",
        ).pack(side="left")

        ctk.CTkLabel(
            title_frame,
            text=f" v{self.APP_VERSION} ",
            font=(BASE, 10), text_color="#90CDF4",
            fg_color=colors.PRIMARY_LIGHT,
            corner_radius=10, height=22,
        ).pack(side="left", padx=8)

        if self.APP_SUBTITLE:
            ctk.CTkLabel(
                left, text=self.APP_SUBTITLE,
                font=(BASE, 12), text_color="#A0AEC0",
            ).pack(side="left", padx=4)

        # Breadcrumb area
        self._breadcrumb = ctk.CTkLabel(
            left, text="", font=(BASE, 11), text_color="#718096",
        )
        self._breadcrumb.pack(side="left", padx=(12, 0))

        # Right side
        right_frame = ctk.CTkFrame(self.header, fg_color="transparent")
        right_frame.pack(side="right", padx=12)

        # Notification badge
        self._notif_frame = ctk.CTkFrame(right_frame, fg_color="transparent")
        self._notif_frame.pack(side="right", padx=(8, 0))

        self._notif_btn = ctk.CTkButton(
            self._notif_frame, text="\u25cf", width=36, height=30,  # ●
            font=(BASE, 14), fg_color="transparent",
            hover_color=colors.PRIMARY_LIGHT,
            text_color="#718096", corner_radius=8,
        )
        self._notif_btn.pack(side="right")

        # Theme toggle
        self.theme_btn = ctk.CTkButton(
            right_frame, text="\u2600 \ub77c\uc774\ud2b8",
            width=90, height=30, font=(BASE, 11),
            fg_color=colors.PRIMARY_LIGHT,
            hover_color="#3B6FA0", corner_radius=15,
            command=self._toggle_theme,
        )
        self.theme_btn.pack(side="right", padx=4)

        # Subclass can add more header buttons here
        self.header_right = right_frame

    def _build_sidebar(self, parent, nav_items):
        """Build collapsible sidebar navigation."""
        w = _SIDEBAR_W_OPEN if self._sidebar_open else _SIDEBAR_W_CLOSED

        self._sidebar = ctk.CTkFrame(
            parent, width=w,
            fg_color=(colors.SURFACE, colors.DARK_BG),
            corner_radius=0,
            border_width=1,
            border_color=(colors.TABLE_BORDER, colors.DARK_BORDER),
        )
        self._sidebar.pack(side="left", fill="y")
        self._sidebar.pack_propagate(False)

        # Nav items
        nav_frame = ctk.CTkFrame(self._sidebar, fg_color="transparent")
        nav_frame.pack(fill="both", expand=True, pady=(8, 0))

        for item_id, label, icon_key in nav_items:
            # Always try ICONS dict first, then use raw key as fallback
            icon_char = ICONS.get(icon_key, icon_key[0].upper() if icon_key else "·")

            btn_frame = ctk.CTkFrame(nav_frame, fg_color="transparent", height=44)
            btn_frame.pack(fill="x", padx=6, pady=1)
            btn_frame.pack_propagate(False)

            if self._sidebar_open:
                btn_text = f"  {label}"
            else:
                btn_text = icon_char

            btn = ctk.CTkButton(
                btn_frame,
                text=btn_text,
                font=(BASE, 13),
                fg_color="transparent",
                hover_color=(colors.SECTION_BG, "#1E293B"),
                text_color=(colors.TEXT_SECONDARY, "#A0AEC0"),
                anchor="w" if self._sidebar_open else "center",
                corner_radius=8, height=40,
                command=lambda pid=item_id: self.navigate(pid),
            )
            btn.pack(fill="x", padx=2)
            self._nav_buttons[item_id] = btn

        # Bottom: app info + version
        bottom = ctk.CTkFrame(self._sidebar, fg_color="transparent")
        bottom.pack(side="bottom", fill="x", padx=8, pady=10)

        # Divider line
        ctk.CTkFrame(
            bottom, height=1,
            fg_color=(colors.TABLE_BORDER, colors.DARK_BORDER),
        ).pack(fill="x", pady=(0, 8))

        if self._sidebar_open:
            ctk.CTkLabel(
                bottom, text=f"{self.APP_TITLE}",
                font=(BASE, 10, "bold"),
                text_color=(colors.TEXT_MUTED, colors.DARK_TEXT_MUTED),
            ).pack(anchor="w")
            ctk.CTkLabel(
                bottom, text=f"v{self.APP_VERSION}",
                font=(BASE, 9),
                text_color=(colors.TEXT_MUTED, "#4A5568"),
            ).pack(anchor="w")

    def _build_statusbar(self):
        """Build enhanced status bar with progress indicator."""
        self.statusbar = ctk.CTkFrame(
            self.root, height=_STATUS_H,
            fg_color=(colors.FOOTER_BG, colors.DARK_BG),
            corner_radius=0,
        )
        self.statusbar.pack(fill="x")
        self.statusbar.pack_propagate(False)

        # Status text
        self.status_label = ctk.CTkLabel(
            self.statusbar, text="\uc900\ube44 \uc644\ub8cc",
            font=(BASE, 10),
            text_color=(colors.TEXT_SECONDARY, colors.DARK_TEXT_MUTED),
        )
        self.status_label.pack(side="left", padx=12)

        # Progress bar (hidden by default)
        self._progress = ctk.CTkProgressBar(
            self.statusbar, width=150, height=4,
            progress_color=colors.ACCENT,
            fg_color=(colors.TABLE_BORDER, colors.DARK_BORDER),
        )
        self._progress.set(0)
        # Not packed yet — call show_progress() to show

        # Right: copyright + timestamp
        ctk.CTkLabel(
            self.statusbar, text=self.APP_COPYRIGHT,
            font=(BASE, 9),
            text_color=(colors.TEXT_MUTED, "#4A5568"),
        ).pack(side="right", padx=12)

        self._time_label = ctk.CTkLabel(
            self.statusbar, text="",
            font=(BASE, 9),
            text_color=(colors.TEXT_MUTED, "#4A5568"),
        )
        self._time_label.pack(side="right", padx=(0, 8))
        self._update_clock()

    # ==================================================================
    # NAVIGATION
    # ==================================================================

    def navigate(self, page_id: str):
        """Switch to a page by ID."""
        if page_id == self._current_page:
            return

        # Hide current page
        if self._current_page and self._current_page in self._pages:
            self._pages[self._current_page].pack_forget()

        # Show new page
        if page_id in self._pages:
            self._pages[page_id].pack(fill="both", expand=True, padx=0, pady=0)

        # Update nav button styles
        for bid, btn in self._nav_buttons.items():
            if bid == page_id:
                btn.configure(
                    fg_color=(colors.PRIMARY, colors.PRIMARY),
                    text_color=("white", "white"),
                    font=(BASE, 13, "bold"),
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    text_color=(colors.TEXT_SECONDARY, "#A0AEC0"),
                    font=(BASE, 13),
                )

        self._current_page = page_id

        # Update breadcrumb
        for item_id, label, _ in self._cached_nav_items:
            if item_id == page_id:
                self._breadcrumb.configure(text=f"/ {label}")
                break

    # ==================================================================
    # SIDEBAR TOGGLE
    # ==================================================================

    def _toggle_sidebar(self):
        """Toggle sidebar between open and collapsed."""
        self._sidebar_open = not self._sidebar_open
        w = _SIDEBAR_W_OPEN if self._sidebar_open else _SIDEBAR_W_CLOSED
        self._sidebar.configure(width=w)

        item_map = {item_id: (label, icon_key) for item_id, label, icon_key in self._cached_nav_items}

        for item_id, btn in self._nav_buttons.items():
            label, icon_key = item_map.get(item_id, ("", ""))
            icon_char = ICONS.get(icon_key, icon_key[0].upper() if icon_key else "·")

            if self._sidebar_open:
                btn.configure(
                    text=f"  {label}",
                    font=(BASE, 13), anchor="w",
                )
            else:
                btn.configure(
                    text=icon_char,
                    font=(BASE, 16), anchor="center",
                )

    # ==================================================================
    # PUBLIC API
    # ==================================================================

    def get_nav_items(self) -> list[tuple[str, str, str]]:
        """Override: return list of (page_id, label, icon_key).
        icon_key matches ICONS dict or a single character.
        """
        return []

    def build_page(self, page_id: str, parent):
        """Override: build UI for a specific page into parent frame."""
        pass

    def build_content(self, parent):
        """Legacy override: build the entire UI (no sidebar mode)."""
        pass

    def set_status(self, text: str):
        """Update status bar text."""
        self.status_label.configure(text=text)

    def show_progress(self, value: float = -1):
        """Show/update progress bar. value in [0,1], or -1 for indeterminate."""
        if not self._progress.winfo_ismapped():
            self._progress.pack(side="left", padx=(8, 0))
        if value < 0:
            self._progress.configure(mode="indeterminate")
            self._progress.start()
        else:
            self._progress.configure(mode="determinate")
            self._progress.stop()
            self._progress.set(min(1.0, max(0.0, value)))

    def hide_progress(self):
        """Hide progress bar."""
        self._progress.stop()
        self._progress.pack_forget()

    def set_notification(self, count: int):
        """Update notification badge count."""
        self._notification_count = count
        if count > 0:
            self._notif_btn.configure(text_color=colors.ACCENT_WARM)
        else:
            self._notif_btn.configure(text_color="#718096")

    # ==================================================================
    # THEME
    # ==================================================================

    def _toggle_theme(self):
        """Toggle between dark and light mode."""
        self._dark_mode = not self._dark_mode
        mode = "dark" if self._dark_mode else "light"
        ctk.set_appearance_mode(mode)
        if self._dark_mode:
            self.theme_btn.configure(text="\u2600 \ub77c\uc774\ud2b8")
        else:
            self.theme_btn.configure(text="\u263e \ub2e4\ud06c")

    # ==================================================================
    # CLOCK
    # ==================================================================

    def _update_clock(self):
        now = datetime.now().strftime("%H:%M")
        self._time_label.configure(text=now)
        self._clock_after_id = self.root.after(30000, self._update_clock)

    # ==================================================================
    # QUIT
    # ==================================================================

    def _quit(self):
        """Clean shutdown: cancel pending callbacks, then destroy."""
        if self._clock_after_id is not None:
            self.root.after_cancel(self._clock_after_id)
            self._clock_after_id = None
        self.root.destroy()

    # ==================================================================
    # RUN
    # ==================================================================

    def run(self):
        """Start the application event loop."""
        self.root.mainloop()
