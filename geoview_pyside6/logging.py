"""Structured JSON logging sidecar for GeoView PySide6 apps.

`setup_logging` in runtime.py configures a human-readable text log at
`~/.geoview/logs/<app>.log`. This module adds a parallel JSON-lines
sidecar at `~/.geoview/logs/json/<app>.jsonl` so Grafana Loki /
Promtail can ingest structured events without parsing free-form text.

Design choices:
- No `structlog` dependency — stdlib `logging` + a tiny JsonFormatter.
  Keeps offline vessel builds from pulling an extra package.
- Both handlers attach to the same logger, so a single `.info(...)`
  call appears in both files.
- JSON schema matches the Promtail pipeline in
  `plans/phase_b/infra/loki/promtail-config.yaml`:
    {timestamp, level, suite, event, logger, module, message, ...extra}
  Apps can add arbitrary kwargs via `extra={"project_id": ..., ...}`
  and they flow into the JSON payload untouched.
- Caller names the "suite" via env `GEOVIEW_SUITE` (default derived
  from app_name). Useful for grouping QC apps under one Loki label.
"""
from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any


_JSON_EXCLUDED_FIELDS = frozenset(
    {
        "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
        "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
        "created", "msecs", "relativeCreated", "thread", "threadName",
        "processName", "process", "asctime", "message", "taskName",
    }
)


class JsonFormatter(logging.Formatter):
    """Emit one JSON object per line (ndjson). Safe for Promtail ingest.

    Schema matches the promtail `json:` expressions:
        timestamp, level, suite, event, logger, module, message,
        + any `extra={...}` kwargs passed at log time.
    """

    def __init__(self, app_name: str, suite: str):
        super().__init__()
        self._app = app_name
        self._suite = suite

    def format(self, record: logging.LogRecord) -> str:
        # Base payload — fields named to line up with the promtail
        # pipeline_stages.json expressions.
        payload: dict[str, Any] = {
            "timestamp": time.strftime(
                "%Y-%m-%dT%H:%M:%S", time.gmtime(record.created)
            ) + f".{int(record.msecs):03d}Z",
            "level": record.levelname,
            "suite": self._suite,
            "event": record.getMessage()[:80],  # short tag for Loki labels
            "logger": record.name,
            "module": record.module,
            "message": record.getMessage(),
            "app": self._app,
        }

        # Caller-supplied extras (extra={"project_id": "PID-42"}).
        for key, value in record.__dict__.items():
            if key in _JSON_EXCLUDED_FIELDS:
                continue
            if key.startswith("_"):
                continue
            if key in payload:
                continue
            try:
                json.dumps(value)  # reject non-serialisable values
                payload[key] = value
            except (TypeError, ValueError):
                payload[key] = repr(value)

        if record.exc_info:
            payload["exc_type"] = record.exc_info[0].__name__ if record.exc_info[0] else None
            payload["exc_text"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False, default=str)


def get_json_log_path(app_name: str) -> Path:
    """`~/.geoview/logs/json/<app>.jsonl`."""
    from geoview_pyside6.runtime import get_log_dir  # local import avoids cycle

    safe = "".join(ch if ch.isalnum() or ch in {"-", "_", " "} else "_" for ch in app_name).strip()
    safe = safe or "GeoView"
    json_dir = get_log_dir() / "json"
    json_dir.mkdir(parents=True, exist_ok=True)
    return json_dir / f"{safe}.jsonl"


def attach_json_sidecar(
    logger: logging.Logger,
    app_name: str,
    *,
    suite: str | None = None,
    level: int = logging.INFO,
) -> logging.Handler | None:
    """Add a JSON-lines FileHandler to `logger` once. Idempotent —
    re-invocations with the same target file are no-ops.

    Returns the handler attached on first call, None on subsequent
    invocations (or on unrecoverable IO failure).
    """
    target = get_json_log_path(app_name)
    target_str = str(target.resolve())

    for existing in logger.handlers:
        if isinstance(existing, logging.FileHandler) and getattr(existing, "_geoview_json", False):
            if getattr(existing, "baseFilename", "") == target_str:
                existing.setLevel(level)
                return None

    resolved_suite = suite or os.environ.get("GEOVIEW_SUITE") or app_name
    try:
        handler = logging.FileHandler(target, encoding="utf-8")
    except OSError:
        return None
    handler.setLevel(level)
    handler.setFormatter(JsonFormatter(app_name=app_name, suite=resolved_suite))
    handler._geoview_json = True  # type: ignore[attr-defined]
    logger.addHandler(handler)
    return handler
