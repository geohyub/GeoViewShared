"""Optional Sentry error reporting for GeoView PySide6 apps.

W1 Phase B prep: this module is a no-op unless a ``<APP>_SENTRY_DSN``
environment variable is set (e.g. ``QCHUB_SENTRY_DSN``). When the DSN
is present AND ``sentry_sdk`` is importable, exceptions are captured
with the app name + version + release channel tags.

Phase B (W34+) will wire this into `run_with_crash_dialog` after the
shared Sentry project is provisioned. For now the call is a no-op so
apps can adopt the hook early without breaking offline builds.

Usage:

    from geoview_pyside6.observability import maybe_init_sentry
    maybe_init_sentry(app_name="QCHub", version="1.2.3")
"""
from __future__ import annotations

import os
import sys
from typing import Optional


def _resolve_dsn(app_name: str) -> Optional[str]:
    """Look for ``<APP>_SENTRY_DSN`` first (per-app), then the portfolio
    fallback ``GEOVIEW_SENTRY_DSN``. Returns None when neither is set."""
    app_env = f"{app_name.upper().replace('-', '_').replace(' ', '_')}_SENTRY_DSN"
    dsn = os.environ.get(app_env, "").strip()
    if dsn:
        return dsn
    fallback = os.environ.get("GEOVIEW_SENTRY_DSN", "").strip()
    return fallback or None


def maybe_init_sentry(app_name: str, version: str = "dev") -> bool:
    """Initialise sentry_sdk if a DSN is configured and sentry_sdk is
    importable. Returns True when initialisation actually happened.

    Safe to call unconditionally at startup — on a vessel offline
    deployment without sentry_sdk or a DSN this silently no-ops.
    """
    dsn = _resolve_dsn(app_name)
    if not dsn:
        return False
    try:
        import sentry_sdk  # type: ignore
    except ImportError:
        return False

    sentry_sdk.init(
        dsn=dsn,
        release=f"{app_name}@{version}",
        environment=os.environ.get("GEOVIEW_ENV", "production"),
        # Respect operator's bandwidth — surveys often run with
        # heavily throttled internet. Buffer locally and ship in
        # batches; drop events when the queue is full rather than
        # blocking the UI thread.
        max_breadcrumbs=50,
        shutdown_timeout=2,
        default_integrations=True,
    )
    sentry_sdk.set_tag("app", app_name)
    sentry_sdk.set_tag("python_version", sys.version.split(" ", 1)[0])
    return True
