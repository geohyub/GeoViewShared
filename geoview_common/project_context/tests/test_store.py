"""ProjectContextStore 단위 테스트."""

import json
from pathlib import Path

import pytest

from geoview_common.project_context.models import ProjectContext, ProjectPaths
from geoview_common.project_context.store import ProjectContextStore


@pytest.fixture
def store(tmp_path):
    """임시 디렉토리 기반 Store."""
    return ProjectContextStore(root=tmp_path)


@pytest.fixture
def sample_ctx():
    return ProjectContext(
        project_name="Orsted Taiwan 2026",
        project_code="ORS-TW-2026",
        client="Orsted",
        vessel="MV Explorer",
        crs_epsg=32651,
    )


class TestStoreInit:
    def test_dirs_created(self, store, tmp_path):
        assert (tmp_path / "projects").is_dir()

    def test_root_property(self, store, tmp_path):
        assert store.root == tmp_path


class TestStoreActivation:
    def test_no_active_initially(self, store):
        assert store.get_active_id() is None

    def test_set_and_get_active(self, store, sample_ctx):
        store.save(sample_ctx)
        store.set_active_id(sample_ctx.project_id)
        assert store.get_active_id() == sample_ctx.project_id

    def test_load_active(self, store, sample_ctx):
        store.save_and_activate(sample_ctx)
        ctx = store.load_active()
        assert ctx is not None
        assert ctx.project_name == "Orsted Taiwan 2026"

    def test_load_active_none(self, store):
        assert store.load_active() is None

    def test_clear_active(self, store, sample_ctx):
        store.save_and_activate(sample_ctx)
        store.clear_active()
        assert store.get_active_id() is None
        assert store.load_active() is None


class TestStoreCRUD:
    def test_save_and_load(self, store, sample_ctx):
        store.save(sample_ctx)
        loaded = store.load(sample_ctx.project_id)
        assert loaded is not None
        assert loaded.project_name == sample_ctx.project_name

    def test_exists(self, store, sample_ctx):
        assert not store.exists(sample_ctx.project_id)
        store.save(sample_ctx)
        assert store.exists(sample_ctx.project_id)

    def test_delete(self, store, sample_ctx):
        store.save_and_activate(sample_ctx)
        assert store.delete(sample_ctx.project_id)
        assert not store.exists(sample_ctx.project_id)
        # Active should be cleared
        assert store.get_active_id() is None

    def test_delete_nonexistent(self, store):
        assert not store.delete("nonexistent")

    def test_load_nonexistent(self, store):
        assert store.load("nonexistent") is None


class TestStoreList:
    def test_get_all_empty(self, store):
        assert store.get_all() == []

    def test_get_all(self, store):
        for i in range(3):
            ctx = ProjectContext(project_name=f"Project {i}")
            store.save(ctx)
        assert len(store.get_all()) == 3

    def test_get_recent(self, store):
        for i in range(7):
            ctx = ProjectContext(project_name=f"Project {i}")
            store.save(ctx)
        recent = store.get_recent(5)
        assert len(recent) == 5

    def test_get_by_code(self, store, sample_ctx):
        store.save(sample_ctx)
        found = store.get_by_code("ORS-TW-2026")
        assert found is not None
        assert found.project_id == sample_ctx.project_id

    def test_get_by_code_not_found(self, store):
        assert store.get_by_code("NONE") is None

    def test_search(self, store):
        ctx1 = ProjectContext(project_name="Orsted Taiwan", client="Orsted")
        ctx2 = ProjectContext(project_name="JAKO Korea", client="JAKO")
        store.save(ctx1)
        store.save(ctx2)

        results = store.search("orsted")
        assert len(results) == 1
        assert results[0].client == "Orsted"

        results = store.search("korea")
        assert len(results) == 1
        assert results[0].project_name == "JAKO Korea"

    def test_sorted_by_updated(self, store):
        import time
        ctx1 = ProjectContext(project_name="Old")
        store.save(ctx1)
        time.sleep(0.05)
        ctx2 = ProjectContext(project_name="New")
        store.save(ctx2)

        all_ctx = store.get_all()
        assert all_ctx[0].project_name == "New"
        assert all_ctx[1].project_name == "Old"


class TestStoreCorruption:
    def test_corrupted_active_file(self, store):
        store.active_file.write_text("not json", encoding="utf-8")
        assert store.get_active_id() is None

    def test_corrupted_project_file(self, store, sample_ctx):
        store.save(sample_ctx)
        # Corrupt the file
        f = store.projects_dir / f"{sample_ctx.project_id}.json"
        f.write_text("{{broken", encoding="utf-8")
        assert store.load(sample_ctx.project_id) is None
