"""Shared fixtures for ctk_widgets tests."""

import sys
import pytest


def _display_available() -> bool:
    """Check whether a display server is reachable (X11 / Wayland / Win32)."""
    if sys.platform == "win32":
        return True  # Windows always has a display
    import os
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


def _ctk_available() -> bool:
    """Check whether customtkinter can be imported."""
    try:
        import customtkinter  # noqa: F401
        return True
    except ImportError:
        return False


# Markers for conditional skipping
skip_no_ctk = pytest.mark.skipif(
    not _ctk_available(),
    reason="customtkinter not installed",
)

skip_no_display = pytest.mark.skipif(
    not _display_available(),
    reason="no display available (headless environment)",
)

skip_no_gui = pytest.mark.skipif(
    not (_ctk_available() and _display_available()),
    reason="GUI tests require customtkinter + display",
)


# Session-scoped CTk root — avoids Tk reinitialisation issues
# (creating multiple CTk() instances can fail on some platforms).
@pytest.fixture(scope="session")
def _shared_ctk_root():
    """Create a single hidden CTk root for the entire test session."""
    if not (_ctk_available() and _display_available()):
        pytest.skip("GUI tests require customtkinter + display")
    import customtkinter as ctk
    root = ctk.CTk()
    root.withdraw()
    yield root
    root.destroy()
