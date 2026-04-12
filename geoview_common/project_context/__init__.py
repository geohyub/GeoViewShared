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
from geoview_common.project_context.integration import (
    AppLaunchSpec,
    APP_LAUNCH_REGISTRY,
    build_project_summary,
    build_launch_command,
    create_handoff_file,
    get_app_launch_spec,
    get_context_file_path,
    iter_existing_project_paths,
    launch_registered_app,
    load_handoff,
    load_handoff_from_env,
    sync_project_context_from_project,
)
from geoview_common.project_context.store import ProjectContextStore

__all__ = [
    "ProjectContext",
    "ProjectPaths",
    "ProjectContextStore",
    "AppLaunchSpec",
    "APP_LAUNCH_REGISTRY",
    "build_project_summary",
    "build_launch_command",
    "create_handoff_file",
    "get_app_launch_spec",
    "get_context_file_path",
    "iter_existing_project_paths",
    "launch_registered_app",
    "load_handoff",
    "load_handoff_from_env",
    "sync_project_context_from_project",
]
