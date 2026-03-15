"""
GeoView Base Application
========================
Standard CustomTkinter application frame with:
- GeoView branding (title, version badge)
- Dark/Light theme toggle
- Menu bar support
- Status bar
- Keyboard shortcuts

Usage:
    from geoview_common.ctk_widgets.base_app import GeoViewApp

    class MyApp(GeoViewApp):
        APP_TITLE = "My Tool"
        APP_VERSION = "1.0"

        def build_content(self, parent):
            # Build your UI here
            ...

    if __name__ == "__main__":
        app = MyApp()
        app.run()
"""

import sys
from pathlib import Path
from typing import Optional

try:
    import customtkinter as ctk
    HAS_CTK = True
except ImportError:
    HAS_CTK = False

from ..styles import colors
from ..styles.fonts import BASE


class GeoViewApp:
    """Base class for GeoView CustomTkinter applications."""

    APP_TITLE = "GeoView Application"
    APP_VERSION = "1.0"
    APP_COPYRIGHT = "Copyright (c) 2025-2026 Geoview Co., Ltd."
    WINDOW_SIZE = "1400x900"
    WINDOW_MIN_SIZE = (1200, 700)

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
        self._build_layout()

    def _build_layout(self):
        """Build the standard app layout."""
        # Header bar
        self.header = ctk.CTkFrame(self.root, height=50,
                                    fg_color=colors.PRIMARY)
        self.header.pack(fill="x")
        self.header.pack_propagate(False)

        # Title label
        self.title_label = ctk.CTkLabel(
            self.header,
            text=f"  {self.APP_TITLE}",
            font=(BASE, 14, "bold"),
            text_color="white",
        )
        self.title_label.pack(side="left", padx=10)

        # Version badge
        self.version_label = ctk.CTkLabel(
            self.header,
            text=f" v{self.APP_VERSION} ",
            font=(BASE, 10),
            text_color="white",
            fg_color=colors.PRIMARY_LIGHT,
            corner_radius=8,
        )
        self.version_label.pack(side="left", padx=5)

        # Theme toggle button
        self.theme_btn = ctk.CTkButton(
            self.header,
            text="Light",
            width=60,
            height=28,
            font=(BASE, 9),
            command=self._toggle_theme,
        )
        self.theme_btn.pack(side="right", padx=10)

        # Main content area (for subclass to fill)
        self.content = ctk.CTkFrame(self.root)
        self.content.pack(fill="both", expand=True)

        # Status bar
        self.statusbar = ctk.CTkFrame(self.root, height=28,
                                       fg_color=colors.FOOTER_BG)
        self.statusbar.pack(fill="x")
        self.statusbar.pack_propagate(False)

        self.status_label = ctk.CTkLabel(
            self.statusbar,
            text="Ready",
            font=(BASE, 9),
            text_color=colors.TEXT_SECONDARY,
        )
        self.status_label.pack(side="left", padx=10)

        # Let subclass build content
        self.build_content(self.content)

    def build_content(self, parent):
        """Override in subclass to build the main UI."""
        pass

    def set_status(self, text: str):
        """Update status bar text."""
        self.status_label.configure(text=text)

    def _toggle_theme(self):
        """Toggle between dark and light mode."""
        self._dark_mode = not self._dark_mode
        mode = "dark" if self._dark_mode else "light"
        ctk.set_appearance_mode(mode)
        self.theme_btn.configure(
            text="Light" if self._dark_mode else "Dark"
        )

    def run(self):
        """Start the application event loop."""
        self.root.mainloop()
