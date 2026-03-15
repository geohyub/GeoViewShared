"""
GeoView Styled Widgets
======================
Reusable CustomTkinter widgets with GeoView branding.
"""

try:
    import customtkinter as ctk
    HAS_CTK = True
except ImportError:
    HAS_CTK = False

from ..styles import colors
from ..styles.fonts import BASE


class ParamInput:
    """
    A labeled input field for calculator parameters.

    Creates: [Label] [Entry] [Unit]
    Supports: input mode (editable) and result mode (read-only highlight)
    """

    def __init__(self, parent, label: str, unit: str = "",
                 default: str = "", readonly: bool = False,
                 width: int = 120, row: int = 0):
        if not HAS_CTK:
            raise ImportError("customtkinter required")

        self.frame = ctk.CTkFrame(parent, fg_color="transparent")

        self.label = ctk.CTkLabel(
            self.frame, text=label, font=(BASE, 9),
            width=180, anchor="w"
        )
        self.label.grid(row=0, column=0, padx=(5, 5), sticky="w")

        self.var = ctk.StringVar(value=default)
        fg = colors.RESULT_BG if readonly else colors.INPUT_BG
        state = "disabled" if readonly else "normal"

        self.entry = ctk.CTkEntry(
            self.frame, textvariable=self.var,
            width=width, font=(BASE, 9),
            state=state,
        )
        self.entry.grid(row=0, column=1, padx=5)

        if unit:
            self.unit_label = ctk.CTkLabel(
                self.frame, text=unit, font=(BASE, 8),
                text_color=colors.TEXT_MUTED, width=50, anchor="w"
            )
            self.unit_label.grid(row=0, column=2, padx=5, sticky="w")

    def get(self) -> str:
        return self.var.get()

    def get_float(self, default: float = 0.0) -> float:
        try:
            return float(self.var.get())
        except (ValueError, TypeError):
            return default

    def set(self, value):
        self.var.set(str(value))

    def pack(self, **kwargs):
        self.frame.pack(**kwargs)

    def grid(self, **kwargs):
        self.frame.grid(**kwargs)


class ResultCard:
    """
    A result display card with colored background.

    Shows: [Title]
           [Value] [Unit]
    """

    def __init__(self, parent, title: str, value: str = "-",
                 unit: str = "", status: str = "normal"):
        if not HAS_CTK:
            raise ImportError("customtkinter required")

        bg = {
            "normal": colors.SURFACE,
            "good": colors.GOOD,
            "warn": colors.WARN,
            "danger": colors.DANGER,
        }.get(status, colors.SURFACE)

        self.frame = ctk.CTkFrame(parent, fg_color=bg, corner_radius=8)

        self.title_label = ctk.CTkLabel(
            self.frame, text=title, font=(BASE, 8),
            text_color=colors.TEXT_SECONDARY,
        )
        self.title_label.pack(padx=10, pady=(8, 2))

        self.value_var = ctk.StringVar(value=value)
        self.value_label = ctk.CTkLabel(
            self.frame, textvariable=self.value_var,
            font=(BASE, 16, "bold"),
            text_color=colors.TEXT_PRIMARY,
        )
        self.value_label.pack(padx=10, pady=(0, 2))

        if unit:
            self.unit_label = ctk.CTkLabel(
                self.frame, text=unit, font=(BASE, 8),
                text_color=colors.TEXT_MUTED,
            )
            self.unit_label.pack(padx=10, pady=(0, 8))

    def update(self, value: str, status: str = "normal"):
        self.value_var.set(value)
        bg = {
            "normal": colors.SURFACE,
            "good": colors.GOOD,
            "warn": colors.WARN,
            "danger": colors.DANGER,
        }.get(status, colors.SURFACE)
        self.frame.configure(fg_color=bg)

    def pack(self, **kwargs):
        self.frame.pack(**kwargs)

    def grid(self, **kwargs):
        self.frame.grid(**kwargs)


class SectionHeader:
    """A styled section header with navy background."""

    def __init__(self, parent, text: str):
        self.frame = ctk.CTkFrame(parent, height=32,
                                   fg_color=colors.PRIMARY,
                                   corner_radius=6)
        self.label = ctk.CTkLabel(
            self.frame, text=f"  {text}",
            font=(BASE, 10, "bold"),
            text_color="white", anchor="w",
        )
        self.label.pack(fill="x", padx=10, pady=5)

    def pack(self, **kwargs):
        self.frame.pack(**kwargs)

    def grid(self, **kwargs):
        self.frame.grid(**kwargs)
