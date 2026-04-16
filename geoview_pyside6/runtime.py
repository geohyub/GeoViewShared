from __future__ import annotations

import logging
import os
import sys
import traceback
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication, QMessageBox, QWidget


_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


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


def run_with_crash_dialog(app_name: str, callback: Callable[[], int | None]) -> int:
    logger = setup_logging(app_name)
    install_exception_hook(app_name)
    try:
        result = callback()
    except Exception:
        logger.critical("Fatal error during startup", exc_info=True)
        show_fatal_error(app_name, get_log_file_path(app_name), traceback.format_exc())
        return 1
    return int(result or 0)
