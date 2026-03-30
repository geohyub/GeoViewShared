"""
GeoView Project Context
========================
Shared project context layer for cross-app project settings.

Usage::

    from geoview_common.project_context import (
        ProjectContext, ProjectPaths, ProjectContextStore,
    )

    store = ProjectContextStore()
    ctx = store.load_active()
    if ctx:
        print(ctx.project_name, ctx.paths.raw_data)

Copyright (c) 2025-2026 Geoview Co., Ltd.
"""

from geoview_common.project_context.models import ProjectContext, ProjectPaths
from geoview_common.project_context.store import ProjectContextStore

__all__ = [
    "ProjectContext",
    "ProjectPaths",
    "ProjectContextStore",
]
