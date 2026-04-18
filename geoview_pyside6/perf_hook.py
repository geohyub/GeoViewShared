"""Perf-benchmark auto-quit hook.

Installs a QApplication.exec() wrapper that, when
``GEOVIEW_AUTO_QUIT_MS`` is set, schedules ``QTimer.singleShot(ms,
app.quit)`` + emits ``GEOVIEW_WINDOW_READY`` on the first event-loop
tick. Unlike the equivalent inside ``GeoViewApp.run()`` this works for
any app — including custom launchers that build their own
``QApplication`` and call ``app.exec()`` directly.

Usage (from perf_benchmark.py prelude, before the app module imports)::

    import geoview_pyside6.perf_hook  # side-effect installs the hook

The hook is a no-op when ``GEOVIEW_AUTO_QUIT_MS`` is unset or
non-numeric, so it is safe to leave imported in normal runs too.
"""
from __future__ import annotations

import os
import sys


def _install() -> None:
    ms_raw = os.environ.get("GEOVIEW_AUTO_QUIT_MS", "").strip()
    if not ms_raw.isdigit():
        return
    ms = int(ms_raw)
    if ms <= 0:
        return

    try:
        from PySide6.QtCore import QTimer
        from PySide6.QtWidgets import QApplication
    except Exception:
        return

    original_exec = QApplication.exec
    marker_emitted = {"v": False}

    def _emit_marker() -> None:
        if marker_emitted["v"]:
            return
        marker_emitted["v"] = True
        try:
            print("GEOVIEW_WINDOW_READY", flush=True)
        except Exception:
            pass

    def patched_exec(self, *args, **kwargs):
        QTimer.singleShot(ms, self.quit)
        QTimer.singleShot(0, _emit_marker)
        # PySide6's QApplication.exec is a slot that accepts 0 args
        # when called via the Python wrapper — calling
        # ``original_exec(self)`` raises "takes no arguments (1 given)".
        # Try both call shapes to accommodate version differences.
        try:
            return original_exec(self, *args, **kwargs)
        except TypeError:
            return original_exec()

    QApplication.exec = patched_exec
    # Some code paths still use the deprecated exec_ alias.
    if hasattr(QApplication, "exec_"):
        QApplication.exec_ = patched_exec


_install()
