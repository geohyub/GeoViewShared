"""Project context integration helper tests."""

from __future__ import annotations

from pathlib import Path

from geoview_common.project_context.integration import (
    build_project_summary,
    build_launch_command,
    create_handoff_file,
    get_app_launch_spec,
    iter_existing_project_paths,
    load_handoff,
    sync_project_context_from_project,
)
from geoview_common.project_context.models import ProjectContext, ProjectPaths
from geoview_common.project_context.store import ProjectContextStore


def test_sync_project_context_reuses_existing_app_link(tmp_path):
    store = ProjectContextStore(root=tmp_path)
    existing = ProjectContext(
        project_name="Old Name",
        metadata={
            "integration": {
                "app_links": {
                    "NavQC": {"project_id": "7"}
                }
            }
        },
    )
    store.save(existing)

    ctx = sync_project_context_from_project(
        "NavQC",
        {"id": 7, "name": "Updated Nav Project", "client": "GeoView", "coord_system": "UTM 52N"},
        store=store,
    )

    assert ctx.project_id == existing.project_id
    assert ctx.project_name == "Updated Nav Project"
    assert ctx.client == "GeoView"
    assert ctx.crs_epsg == 32652
    assert store.load_active() is not None
    assert store.load_active().project_id == existing.project_id


def test_sync_project_context_derives_raw_data_path_from_files(tmp_path):
    store = ProjectContextStore(root=tmp_path)
    raw_dir = tmp_path / "raw" / "nav"
    raw_dir.mkdir(parents=True)
    file_a = raw_dir / "a.NPD"
    file_b = raw_dir / "b.NPD"
    file_a.write_text("a", encoding="utf-8")
    file_b.write_text("b", encoding="utf-8")

    ctx = sync_project_context_from_project(
        "NavQC",
        {"id": 11, "name": "With Files"},
        store=store,
        files=[
            {"file_path": str(file_a)},
            {"file_path": str(file_b)},
        ],
    )

    assert Path(ctx.paths.raw_data) == raw_dir


def test_create_handoff_file_roundtrip(tmp_path):
    ctx = ProjectContext(project_name="Bridge Project")
    path, payload = create_handoff_file(
        "NavQC",
        "QCHub",
        project_context=ctx,
        payload={"line_id": 12},
        root=tmp_path,
    )

    loaded = load_handoff(path)
    assert payload["handoff_id"] == loaded["handoff_id"]
    assert loaded["project_context_id"] == ctx.project_id
    assert loaded["payload"]["line_id"] == 12


def test_build_launch_command_sets_context_env():
    spec = get_app_launch_spec("NavQC")
    assert spec is not None

    cmd, cwd, env = build_launch_command(
        "NavQC",
        project_file="E:/Software/.geoview/projects/demo.json",
        handoff_file="E:/Software/.geoview/handoffs/demo.json",
        python_executable="python",
    )

    assert cmd == ["python", "-m", "desktop.main"]
    assert cwd == spec.root
    assert env["GEOVIEW_PROJECT_FILE"].endswith("demo.json")
    assert env["GEOVIEW_HANDOFF_FILE"].endswith("demo.json")


def test_iter_existing_project_paths_deduplicates_and_filters(tmp_path):
    raw_dir = tmp_path / "raw"
    reports_dir = tmp_path / "reports"
    raw_dir.mkdir()
    reports_dir.mkdir()
    ctx = ProjectContext(
        project_name="Paths",
        paths=ProjectPaths(
            raw_data=str(raw_dir),
            processed_data=str(raw_dir),
            reports=str(reports_dir),
            delivery=str(tmp_path / "missing"),
        ),
    )

    items = iter_existing_project_paths(ctx)

    assert items == [
        ("Raw Data", raw_dir.resolve()),
        ("Reports", reports_dir.resolve()),
    ]


def test_build_project_summary_includes_core_fields(tmp_path):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    ctx = ProjectContext(
        project_name="Bridge",
        project_code="BR-01",
        client="GeoView",
        vessel="Explorer",
        crs_name="UTM 52N",
        paths=ProjectPaths(raw_data=str(raw_dir)),
    )

    text = build_project_summary(ctx)

    assert "Project: [BR-01] Bridge" in text
    assert "Client: GeoView" in text
    assert "Vessel: Explorer" in text
    assert "CRS: UTM 52N" in text
    assert str(raw_dir.resolve()) in text
