"""Build-time declarative hints for PyInstaller specs.

Each GeoView PySide6 app spec should pull its `hiddenimports` and
`excludes` from here so the portfolio ships one coherent Qt surface.
When one app learns that `PySide6.QtSvg` (or any other quiet
side-effect module) is required at runtime, adding it here means
every spec benefits next time it rebuilds.

Usage inside a .spec:

    from _shared.geoview_pyside6._build_hooks import (
        COMMON_QT_HIDDEN, COMMON_SCI_HIDDEN,
        COMMON_EXCLUDES, forbidden_alt_qt_bindings,
    )

    hiddenimports = [
        *COMMON_QT_HIDDEN,
        *COMMON_SCI_HIDDEN,
        # app-specific adds
    ]
    excludes = [*COMMON_EXCLUDES, *forbidden_alt_qt_bindings()]
"""
from __future__ import annotations

# ── Qt runtime modules that don't always appear on the static import
# graph but are loaded dynamically by PySide6 / pyqtgraph / matplotlib
# at first-window construction. Missing any of these crashes the app
# on launch with ModuleNotFoundError or a silent "qwindows" load
# failure.
COMMON_QT_HIDDEN: list[str] = [
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "PySide6.QtSvg",            # used by pyqtgraph icons + many widgets
    "PySide6.QtSvgWidgets",     # QSvgWidget via pyqtgraph
    "PySide6.QtPrintSupport",   # used by matplotlib Qt backend's save dialog
    "PySide6.QtNetwork",        # needed by Qt docs / tooltip image downloads
    "PySide6.QtOpenGL",         # pulled in by pyqtgraph's GL path
    "PySide6.QtOpenGLWidgets",
    "PySide6.QtXml",
]

# pyqtgraph + matplotlib + openpyxl that almost every QC / Processing
# app touches.
COMMON_SCI_HIDDEN: list[str] = [
    "pyqtgraph",
    "pyqtgraph.exporters",
    "pyqtgraph.graphicsItems",
    "matplotlib",
    "matplotlib.backends.backend_qtagg",
    "matplotlib.backends.backend_agg",
    "matplotlib.figure",
    "numpy",
    "openpyxl",
]

# Dev-only / non-runtime modules that ballooned past builds. Keep the
# list tight:
#   - `setuptools` / `distutils` caused MagQC "ExcludedModule already
#     imported" failures (BL-016 v1 → 9b3903e).
#   - `pydoc` / `doctest` / `unittest` are used by pyqtgraph
#     (parametertree.interactive imports pydoc) and by mpl's test
#     harnesses. Excluding them crashes the app at first import with
#     `ModuleNotFoundError: No module named 'pydoc'` (BL-016 v2 find).
#   - `pdb` is occasionally hit by faulthandler tracebacks.
# Only exclude things we're confident never get transitively imported
# by the runtime graph.
COMMON_EXCLUDES: list[str] = [
    "customtkinter",
    "tkinter",
    "IPython", "jupyter", "jupyter_client", "jupyter_core",
    "notebook", "nbformat", "nbconvert", "nbclient",
    "sphinx", "docutils",
    "debugpy", "coverage",
]


def forbidden_alt_qt_bindings() -> list[str]:
    """Alternate Qt bindings must never ship alongside PySide6."""
    return ["PyQt5", "PyQt6", "PySide2"]
