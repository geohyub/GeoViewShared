"""
GeoView Project Context - Integration Helpers
=============================================
QC 앱 간 연동을 위한 공용 컨텍스트 동기화/핸드오프/실행 헬퍼.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from geoview_common.project_context.models import ProjectContext
from geoview_common.project_context.store import ProjectContextStore


_DEFAULT_HANDOFF_ROOT = Path("E:/Software/.geoview/handoffs")


@dataclass(frozen=True)
class AppLaunchSpec:
    app_name: str
    root: Path
    module: str = "desktop.main"


APP_LAUNCH_REGISTRY: dict[str, AppLaunchSpec] = {
    "magqc": AppLaunchSpec("MagQC", Path("E:/Software/QC/MagQC")),
    "mbesqc": AppLaunchSpec("MBESQC", Path("E:/Software/QC/MBESQC")),
    "navqc": AppLaunchSpec("NavQC", Path("E:/Software/QC/NavQC")),
    "qchub": AppLaunchSpec("QCHub", Path("E:/Software/QC/QCHub")),
    "seismicqc": AppLaunchSpec("SeismicQC", Path("E:/Software/QC/SeismicQC")),
    "sonarqc": AppLaunchSpec("SonarQC", Path("E:/Software/QC/SonarQC")),
}

_PATH_LABELS: tuple[tuple[str, str], ...] = (
    ("raw_data", "Raw Data"),
    ("processed_data", "Processed Data"),
    ("qc_output", "QC Output"),
    ("reports", "Reports"),
    ("delivery", "Delivery"),
    ("nas_primary", "NAS Primary"),
    ("nas_backup", "NAS Backup"),
)


def _normalize_app_name(app_name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(app_name or "").lower())


def _extract_epsg(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, int):
        return value if value > 0 else 0
    text = str(value).strip()
    if not text:
        return 0

    match = re.search(r"(\d{4,5})", text)
    if match:
        code = int(match.group(1))
        if 1024 <= code <= 99999:
            return code

    utm = re.search(r"UTM\s*(\d+)\s*([NS])?", text, re.IGNORECASE)
    if utm:
        zone = int(utm.group(1))
        hemi = (utm.group(2) or "N").upper()
        return 32600 + zone if hemi == "N" else 32700 + zone
    return 0


def _merge_dict(dst: dict[str, Any], src: Mapping[str, Any]) -> dict[str, Any]:
    for key, value in src.items():
        if isinstance(value, Mapping) and isinstance(dst.get(key), dict):
            _merge_dict(dst[key], value)
        else:
            dst[key] = value
    return dst


def get_app_launch_spec(app_name: str) -> AppLaunchSpec | None:
    return APP_LAUNCH_REGISTRY.get(_normalize_app_name(app_name))


def iter_existing_project_paths(ctx: ProjectContext | None) -> list[tuple[str, Path]]:
    """Return user-facing project paths that currently exist."""
    if ctx is None or not getattr(ctx, "paths", None):
        return []

    seen: set[str] = set()
    items: list[tuple[str, Path]] = []
    for attr, label in _PATH_LABELS:
        raw = str(getattr(ctx.paths, attr, "") or "").strip()
        if not raw:
            continue
        try:
            path = Path(raw).resolve()
        except OSError:
            continue
        if not path.exists():
            continue
        key = str(path).lower()
        if key in seen:
            continue
        seen.add(key)
        items.append((label, path))
    return items


def build_project_summary(ctx: ProjectContext | None) -> str:
    """Compact multi-line project summary for clipboard or quick sharing."""
    if ctx is None:
        return "No active project"

    lines = [
        f"Project: {ctx.display_name()}",
    ]
    if ctx.client:
        lines.append(f"Client: {ctx.client}")
    if ctx.vessel:
        lines.append(f"Vessel: {ctx.vessel}")
    if ctx.survey_area:
        lines.append(f"Area: {ctx.survey_area}")
    if ctx.crs_name:
        lines.append(f"CRS: {ctx.crs_name}")
    elif ctx.crs_epsg:
        lines.append(f"CRS: EPSG:{ctx.crs_epsg}")
    for label, path in iter_existing_project_paths(ctx):
        lines.append(f"{label}: {path}")
    return "\n".join(lines)


def _candidate_contexts(store: ProjectContextStore,
                        current_ctx: ProjectContext | None,
                        canonical_app: str,
                        project: Mapping[str, Any]) -> list[ProjectContext]:
    results: list[ProjectContext] = []
    if current_ctx is not None:
        results.append(current_ctx)

    project_id = str(project.get("id") or project.get("project_id") or "").strip()
    project_name = str(project.get("name") or project.get("project_name") or "").strip().lower()
    client = str(project.get("client") or "").strip().lower()

    for ctx in store.get_all():
        if current_ctx is not None and ctx.project_id == current_ctx.project_id:
            continue
        links = (
            (ctx.metadata or {})
            .get("integration", {})
            .get("app_links", {})
        )
        link = links.get(canonical_app) or {}
        linked_project_id = str(link.get("project_id") or "").strip()
        if project_id and linked_project_id == project_id:
            results.insert(0, ctx)
            continue
        if project_name and ctx.project_name.strip().lower() == project_name:
            if client and ctx.client.strip().lower() == client:
                results.append(ctx)
            elif not client:
                results.append(ctx)
    return results


def _derive_raw_data_path(files: list[Mapping[str, Any]] | None) -> str:
    if not files:
        return ""
    parents: list[str] = []
    for item in files:
        file_path = str(item.get("file_path") or "").strip()
        if not file_path:
            continue
        try:
            parent = str(Path(file_path).resolve().parent)
        except OSError:
            continue
        parents.append(parent)
    if not parents:
        return ""
    try:
        return os.path.commonpath(parents)
    except ValueError:
        return parents[0]


def sync_project_context_from_project(app_name: str,
                                      project: Mapping[str, Any],
                                      *,
                                      files: list[Mapping[str, Any]] | None = None,
                                      current_ctx: ProjectContext | None = None,
                                      store: ProjectContextStore | None = None,
                                      path_hints: Mapping[str, str] | None = None,
                                      metadata: Mapping[str, Any] | None = None,
                                      activate: bool = True) -> ProjectContext:
    """Update or create a shared ProjectContext from an app-local project record."""
    store = store or ProjectContextStore()
    spec = get_app_launch_spec(app_name)
    canonical_app = spec.app_name if spec else str(app_name or "GeoView")

    candidates = _candidate_contexts(store, current_ctx, canonical_app, project)
    ctx = candidates[0] if candidates else ProjectContext()

    ctx.project_name = str(project.get("name") or project.get("project_name") or ctx.project_name or "")
    ctx.project_code = str(project.get("project_code") or ctx.project_code or "")
    ctx.client = str(project.get("client") or ctx.client or "")
    ctx.vessel = str(
        project.get("vessel_name")
        or project.get("vessel")
        or ctx.vessel
        or ""
    )
    ctx.survey_area = str(
        project.get("survey_area")
        or project.get("area")
        or ctx.survey_area
        or ""
    )
    ctx.crs_name = str(
        project.get("coord_system")
        or project.get("projection")
        or ctx.crs_name
        or ""
    )
    ctx.crs_epsg = (
        _extract_epsg(project.get("epsg"))
        or _extract_epsg(project.get("coord_system"))
        or _extract_epsg(project.get("projection"))
        or ctx.crs_epsg
    )
    if project.get("offset_config_id") is not None:
        ctx.vessel_config_id = project.get("offset_config_id")
    if project.get("line_prefix"):
        ctx.line_prefix = str(project.get("line_prefix") or "")

    if not isinstance(ctx.metadata, dict):
        ctx.metadata = {}
    integration_meta = ctx.metadata.setdefault("integration", {})
    app_links = integration_meta.setdefault("app_links", {})
    app_links[canonical_app] = {
        "project_id": str(project.get("id") or project.get("project_id") or ""),
        "project_name": ctx.project_name,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "file_count": len(files or []),
    }
    integration_meta["last_active_app"] = canonical_app

    raw_data_path = _derive_raw_data_path(files)
    if raw_data_path:
        ctx.paths.raw_data = raw_data_path

    if path_hints:
        for key, value in path_hints.items():
            if hasattr(ctx.paths, key) and value:
                setattr(ctx.paths, key, str(value))

    if metadata:
        _merge_dict(ctx.metadata, dict(metadata))

    if activate:
        store.save_and_activate(ctx)
    else:
        store.save(ctx)
    return ctx


def get_context_file_path(ctx: ProjectContext,
                          store: ProjectContextStore | None = None) -> Path:
    store = store or ProjectContextStore()
    return store.projects_dir / f"{ctx.project_id}.json"


def create_handoff_file(source_app: str,
                        target_app: str,
                        *,
                        action: str = "open_project",
                        project_context: ProjectContext | None = None,
                        payload: Mapping[str, Any] | None = None,
                        root: str | Path | None = None) -> tuple[Path, dict[str, Any]]:
    """Write a cross-app handoff JSON payload and return its path."""
    handoff_root = Path(root) if root else _DEFAULT_HANDOFF_ROOT
    handoff_root.mkdir(parents=True, exist_ok=True)

    data = {
        "handoff_id": uuid.uuid4().hex[:12],
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "source_app": source_app,
        "target_app": target_app,
        "action": action,
        "project_context_id": getattr(project_context, "project_id", ""),
        "payload": dict(payload or {}),
    }
    path = handoff_root / (
        f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_"
        f"{_normalize_app_name(source_app)}_"
        f"{_normalize_app_name(target_app)}_"
        f"{data['handoff_id']}.json"
    )
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path, data


def load_handoff(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_handoff_from_env() -> dict[str, Any] | None:
    handoff_file = os.environ.get("GEOVIEW_HANDOFF_FILE", "").strip()
    if not handoff_file:
        return None
    path = Path(handoff_file)
    if not path.exists():
        return None
    try:
        return load_handoff(path)
    except (json.JSONDecodeError, OSError):
        return None


def build_launch_command(target_app: str,
                         *,
                         project_file: str | Path | None = None,
                         handoff_file: str | Path | None = None,
                         python_executable: str | None = None,
                         extra_env: Mapping[str, str] | None = None) -> tuple[list[str], Path, dict[str, str]]:
    """Build the command/env needed to launch a registered QC app."""
    spec = get_app_launch_spec(target_app)
    if spec is None:
        raise ValueError(f"Unknown target app: {target_app}")

    env = dict(os.environ)
    if project_file:
        env["GEOVIEW_PROJECT_FILE"] = str(project_file)
    if handoff_file:
        env["GEOVIEW_HANDOFF_FILE"] = str(handoff_file)
    if extra_env:
        env.update({str(k): str(v) for k, v in extra_env.items()})

    cmd = [python_executable or sys.executable, "-m", spec.module]
    return cmd, spec.root, env


def launch_registered_app(target_app: str,
                          *,
                          project_file: str | Path | None = None,
                          handoff_file: str | Path | None = None,
                          python_executable: str | None = None,
                          extra_env: Mapping[str, str] | None = None) -> subprocess.Popen:
    """Launch a registered QC app with optional context/handoff environment."""
    cmd, cwd, env = build_launch_command(
        target_app,
        project_file=project_file,
        handoff_file=handoff_file,
        python_executable=python_executable,
        extra_env=extra_env,
    )
    kwargs: dict[str, Any] = {"cwd": str(cwd), "env": env}
    if os.name == "nt":
        kwargs["creationflags"] = (
            getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            | getattr(subprocess, "DETACHED_PROCESS", 0)
        )
    return subprocess.Popen(cmd, **kwargs)
