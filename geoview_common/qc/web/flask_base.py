"""
QC Flask Base — Shared Flask application factory and Blueprint patterns.
==========================================================================
Provides a standard Flask app creation pattern with:
- GeoView dark theme (gv-theme.css)
- SQLite database setup (WAL mode)
- Common API response helpers
- Template helpers (score badge, status color, etc.)

Usage:
    from geoview_common.qc.web.flask_base import create_qc_app, QCBlueprint

    app = create_qc_app("SonarQC", port=5013)

Copyright (c) 2025-2026 Geoview Co., Ltd.
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Generator

from flask import Flask, jsonify, render_template


# ---------------------------------------------------------------------------
# Database helper (same pattern as MagQC models.py)
# ---------------------------------------------------------------------------

@contextmanager
def get_db(db_path: str) -> Generator[sqlite3.Connection, None, None]:
    """Context manager for SQLite database connections.

    Uses WAL mode for concurrent access, row_factory for dict-like rows.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Flask App Factory
# ---------------------------------------------------------------------------

def create_qc_app(
    app_name: str,
    module_dir: str | Path,
    port: int = 5000,
    db_name: str = "qc.db",
    static_folder: str | Path | None = None,
    template_folder: str | Path | None = None,
) -> Flask:
    """Create a Flask app following GeoView QC conventions.

    Args:
        app_name: Application display name (e.g., "SonarQC").
        module_dir: Directory containing the QC module.
        port: Default port number.
        db_name: SQLite database filename.
        static_folder: Custom static folder (default: module_dir/static).
        template_folder: Custom template folder (default: module_dir/templates).

    Returns:
        Configured Flask app instance.
    """
    module_dir = Path(module_dir)

    if static_folder is None:
        static_folder = module_dir / "static"
    if template_folder is None:
        template_folder = module_dir / "templates"

    app = Flask(
        app_name,
        static_folder=str(static_folder),
        template_folder=str(template_folder),
    )

    # Secret key
    secret_file = module_dir / ".secret_key"
    if secret_file.exists():
        app.secret_key = secret_file.read_text().strip()
    else:
        app.secret_key = os.urandom(32).hex()
        secret_file.write_text(app.secret_key)

    # Config
    app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024  # 500MB
    app.config["DB_PATH"] = str(module_dir / db_name)
    app.config["UPLOAD_FOLDER"] = str(module_dir / "uploads")
    app.config["QC_APP_NAME"] = app_name
    app.config["QC_PORT"] = port

    # Ensure upload directory
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # Template context
    @app.context_processor
    def inject_globals():
        return {
            "app_name": app_name,
            "port": port,
            "now": datetime.now,
        }

    # Common error handlers
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"ok": False, "error": "Not found"}), 404

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({"ok": False, "error": "Internal server error"}), 500

    return app


# ---------------------------------------------------------------------------
# API Response Helpers
# ---------------------------------------------------------------------------

def api_success(data: Any = None, message: str = "") -> tuple:
    """Standard success response."""
    resp = {"ok": True}
    if data is not None:
        resp["data"] = data
    if message:
        resp["message"] = message
    return jsonify(resp), 200


def api_error(message: str, status: int = 400) -> tuple:
    """Standard error response."""
    return jsonify({"ok": False, "error": message}), status


# ---------------------------------------------------------------------------
# Jinja2 Template Helpers
# ---------------------------------------------------------------------------

def register_template_helpers(app: Flask) -> None:
    """Register common Jinja2 filters and globals for QC templates."""

    @app.template_filter("score_color")
    def score_color(score: float) -> str:
        """Return CSS color class for a QC score."""
        if score >= 80:
            return "text-success"
        elif score >= 50:
            return "text-warning"
        return "text-danger"

    @app.template_filter("status_badge")
    def status_badge(status: str) -> str:
        """Return Bootstrap badge class for QC status."""
        mapping = {
            "PASS": "bg-success",
            "WARN": "bg-warning text-dark",
            "FAIL": "bg-danger",
            "N/A": "bg-secondary",
        }
        return mapping.get(status, "bg-secondary")

    @app.template_filter("grade_color")
    def grade_color(grade: str) -> str:
        """Return hex color for letter grade."""
        mapping = {
            "A": "#38A169",
            "B": "#3182CE",
            "C": "#ED8936",
            "D": "#E53E3E",
            "F": "#718096",
        }
        return mapping.get(grade, "#718096")

    @app.template_filter("human_size")
    def human_size(n: int) -> str:
        """Format bytes as human-readable size."""
        for unit in ("B", "KB", "MB", "GB"):
            if abs(n) < 1024:
                return f"{n:,.1f} {unit}"
            n /= 1024
        return f"{n:,.1f} TB"

    @app.template_filter("dt_format")
    def dt_format(dt: datetime | str, fmt: str = "%Y-%m-%d %H:%M") -> str:
        """Format datetime for display."""
        if isinstance(dt, str):
            try:
                dt = datetime.fromisoformat(dt)
            except (ValueError, TypeError):
                return str(dt)
        return dt.strftime(fmt)
