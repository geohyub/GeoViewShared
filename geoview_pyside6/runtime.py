from __future__ import annotations

import logging
import os
import sys
import traceback
from pathlib import Path
from typing import Callable

import PySide6
from PySide6.QtCore import QCoreApplication, QSettings
from PySide6.QtWidgets import QApplication, QMessageBox, QWidget


_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


# ── Qt plugin path auto-registration ──────────────────────────────
# PyInstaller one-folder builds, portable Python distributions, and
# machines with multiple PySide6 installs sometimes fail to locate the
# Qt `platforms/qwindows.dll` (or `libqxcb.so` on Linux) at launch,
# printing "This application failed to start because no Qt platform
# plugin could be initialized" and exiting immediately.
#
# The canonical fix is to tell Qt exactly where the plugins directory
# lives via QCoreApplication.addLibraryPath() BEFORE QApplication is
# constructed. We probe the same `PySide6/plugins` directory the
# running interpreter already imports from, so the lookup is always
# consistent with the resolved binding.

_QT_PLUGIN_PATHS_REGISTERED = False


def _candidate_plugin_dirs() -> list[str]:
    """Return plausible Qt plugin directories, most-preferred first.

    Probes:
    1. `<PySide6 dir>/plugins`           — the active binding
    2. `<PySide6 dir>/Qt6/plugins`       — pip-installed wheel layout
    3. `QT_PLUGIN_PATH` env var          — operator override
    """
    candidates: list[str] = []
    try:
        pyside_dir = Path(PySide6.__file__).resolve().parent
    except (AttributeError, TypeError):
        pyside_dir = None

    if pyside_dir is not None:
        for sub in ("plugins", "Qt6/plugins", "Qt/plugins"):
            candidate = pyside_dir / sub
            if candidate.is_dir():
                candidates.append(str(candidate))

    env_override = os.environ.get("QT_PLUGIN_PATH", "").strip()
    if env_override:
        for part in env_override.split(os.pathsep):
            part = part.strip()
            if part and Path(part).is_dir():
                candidates.append(part)

    # Deduplicate preserving order.
    seen: set[str] = set()
    unique: list[str] = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            unique.append(c)
    return unique


def register_qt_plugin_paths(force: bool = False) -> list[str]:
    """Ensure Qt can find its platform plugins.

    Idempotent: repeated calls are no-ops unless `force=True`.
    Returns the list of plugin directories registered on this call
    (useful for tests and log output).

    Call this BEFORE creating QApplication. `run_with_crash_dialog`
    calls it for you. Standalone scripts that build QApplication
    directly should call it themselves near the top of main().
    """
    global _QT_PLUGIN_PATHS_REGISTERED
    if _QT_PLUGIN_PATHS_REGISTERED and not force:
        return []

    existing: set[str] = set()
    try:
        for entry in QCoreApplication.libraryPaths():
            existing.add(str(Path(entry).resolve()))
    except Exception:
        existing = set()

    added: list[str] = []
    for path in _candidate_plugin_dirs():
        resolved = str(Path(path).resolve())
        if resolved in existing:
            continue
        QCoreApplication.addLibraryPath(path)
        existing.add(resolved)
        added.append(path)

    _QT_PLUGIN_PATHS_REGISTERED = True
    return added


# Register at import time — this runs before any QApplication() call
# as long as the importing app imports `geoview_pyside6` (or this
# module) before instantiating Qt objects, which every GeoView entry
# point already does.
try:
    register_qt_plugin_paths()
except Exception:  # pragma: no cover — never fatal at import
    pass


def _configure_logger(
    logger: logging.Logger,
    *,
    log_file: Path,
    level: int,
    propagate: bool,
) -> logging.Logger:
    logger.setLevel(level)
    logger.propagate = propagate

    formatter = logging.Formatter(_LOG_FORMAT)
    wanted_log_file = str(log_file.resolve())

    has_stream = False
    has_file = False
    for handler in list(logger.handlers):
        if isinstance(handler, logging.FileHandler):
            base_filename = getattr(handler, "baseFilename", "")
            if base_filename == wanted_log_file:
                handler.setLevel(level)
                handler.setFormatter(formatter)
                has_file = True
                continue
            logger.removeHandler(handler)
            handler.close()
            continue
        if type(handler) is logging.StreamHandler:
            if has_stream:
                logger.removeHandler(handler)
                handler.close()
                continue
            handler.setLevel(level)
            handler.setFormatter(formatter)
            has_stream = True

    if not has_file:
        file_handler = logging.FileHandler(wanted_log_file, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    if not has_stream:
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(level)
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

    return logger


def geoview_home() -> Path:
    override = os.environ.get("GEOVIEW_HOME", "").strip()
    if override:
        return Path(override)
    return Path.home() / ".geoview"


def get_log_dir() -> Path:
    log_dir = geoview_home() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def get_log_file_path(app_name: str) -> Path:
    safe_name = "".join(ch if ch.isalnum() or ch in {"-", "_", " "} else "_" for ch in app_name).strip()
    safe_name = safe_name or "GeoView"
    return get_log_dir() / f"{safe_name}.log"


def setup_logging(app_name: str, level: int = logging.INFO) -> logging.Logger:
    log_file = get_log_file_path(app_name)
    root_logger = logging.getLogger()
    _configure_logger(root_logger, log_file=log_file, level=level, propagate=True)

    logger = logging.getLogger(app_name)
    return _configure_logger(logger, log_file=log_file, level=level, propagate=False)


def install_exception_hook(app_name: str) -> None:
    current = getattr(sys, "excepthook", None)
    if getattr(current, "_geoview_app_name", None) == app_name:
        return

    previous = current or sys.__excepthook__

    def _hook(exc_type, exc, tb):
        if issubclass(exc_type, KeyboardInterrupt):
            previous(exc_type, exc, tb)
            return
        logger = setup_logging(app_name)
        logger.critical("Unhandled exception", exc_info=(exc_type, exc, tb))
        exc_text = "".join(traceback.format_exception(exc_type, exc, tb))
        show_fatal_error(app_name, get_log_file_path(app_name), exc_text)

    _hook._geoview_app_name = app_name  # type: ignore[attr-defined]
    sys.excepthook = _hook


def show_fatal_error(
    app_name: str,
    log_file: Path | None = None,
    exc_text: str | None = None,
    parent: QWidget | None = None,
) -> None:
    trace_text = (exc_text or "").strip()
    if trace_text:
        trace_text = trace_text[-1200:]
    log_hint = str(log_file or get_log_file_path(app_name))
    message = (
        "프로그램에서 예기치 않은 오류가 발생했습니다.\n\n"
        f"앱: {app_name}\n"
        f"로그 파일: {log_hint}"
    )
    if trace_text:
        message += f"\n\n최근 오류 정보:\n{trace_text}"

    if QApplication.instance() is None:
        print(message, file=sys.stderr)
        return

    QMessageBox.critical(parent, f"{app_name} 오류", message)


def create_settings(app_name: str, parent: QWidget | None = None) -> QSettings:
    return QSettings("GeoView", app_name, parent)


def restore_window_state(
    window: QWidget,
    settings: QSettings,
    *,
    restore_geometry: bool = True,
    restore_state: bool = True,
) -> None:
    if restore_geometry:
        geometry = settings.value("geometry")
        if geometry:
            window.restoreGeometry(geometry)

    if restore_state and hasattr(window, "restoreState"):
        for key in ("windowState", "dock_state"):
            value = settings.value(key)
            if value:
                window.restoreState(value)
                break


def save_window_state(
    window: QWidget,
    settings: QSettings,
    *,
    save_geometry: bool = True,
    save_state: bool = True,
) -> None:
    if save_geometry and hasattr(window, "saveGeometry"):
        settings.setValue("geometry", window.saveGeometry())

    if save_state and hasattr(window, "saveState"):
        state = window.saveState()
        settings.setValue("windowState", state)
        settings.setValue("dock_state", state)


def run_with_crash_dialog(
    app_name: str,
    callback: Callable[[], int | None],
    *,
    version: str = "dev",
) -> int:
    # Idempotent — import-time registration already ran, but calling
    # again guards against apps that reset QCoreApplication.libraryPaths()
    # in custom setup code.
    register_qt_plugin_paths()
    logger = setup_logging(app_name)
    install_exception_hook(app_name)

    # Phase B W34: opt-in Sentry error reporting. No-op when
    # <APP>_SENTRY_DSN / GEOVIEW_SENTRY_DSN is unset OR sentry_sdk
    # isn't installed — offline vessel deployments stay unaffected.
    try:
        from geoview_pyside6.observability import maybe_init_sentry
        if maybe_init_sentry(app_name=app_name, version=version):
            logger.info("Sentry error reporting enabled (%s@%s)", app_name, version)
    except Exception:
        logger.debug("Sentry init skipped (import or init error)", exc_info=True)

    try:
        result = callback()
    except Exception:
        logger.critical("Fatal error during startup", exc_info=True)
        show_fatal_error(app_name, get_log_file_path(app_name), traceback.format_exc())
        return 1
    return int(result or 0)
