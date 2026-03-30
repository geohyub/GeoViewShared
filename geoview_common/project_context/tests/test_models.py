"""ProjectContext / ProjectPaths 모델 단위 테스트."""

import json
import tempfile
from pathlib import Path

import pytest

from geoview_common.project_context.models import ProjectContext, ProjectPaths


# ── ProjectPaths ──

class TestProjectPaths:
    def test_defaults(self):
        p = ProjectPaths()
        assert p.raw_data == ""
        assert p.nas_backup == ""

    def test_roundtrip_dict(self):
        p = ProjectPaths(raw_data="/data/raw", nas_primary="Z:/NAS1")
        d = p.to_dict()
        p2 = ProjectPaths.from_dict(d)
        assert p2.raw_data == "/data/raw"
        assert p2.nas_primary == "Z:/NAS1"

    def test_from_dict_ignores_unknown(self):
        p = ProjectPaths.from_dict({"raw_data": "/x", "unknown_field": 42})
        assert p.raw_data == "/x"

    def test_validate_empty_paths_ok(self):
        p = ProjectPaths()
        assert p.validate() == []

    def test_validate_nonexistent(self):
        p = ProjectPaths(raw_data="/nonexistent/path/xyz")
        warns = p.validate()
        assert len(warns) == 1
        assert "raw_data" in warns[0]

    def test_validate_skips_empty(self):
        p = ProjectPaths(raw_data="", processed_data="/nonexistent/abc")
        warns = p.validate()
        assert len(warns) == 1
        assert "processed_data" in warns[0]


# ── ProjectContext ──

class TestProjectContext:
    def test_defaults(self):
        ctx = ProjectContext()
        assert ctx.project_name == ""
        assert ctx.timezone_offset == 9.0
        assert isinstance(ctx.paths, ProjectPaths)
        assert isinstance(ctx.metadata, dict)
        assert len(ctx.project_id) == 12

    def test_display_name_both(self):
        ctx = ProjectContext(project_code="ABC", project_name="Test")
        assert ctx.display_name() == "[ABC] Test"

    def test_display_name_only_name(self):
        ctx = ProjectContext(project_name="Test")
        assert ctx.display_name() == "Test"

    def test_display_name_empty(self):
        ctx = ProjectContext()
        assert ctx.display_name() == "(Unnamed Project)"

    def test_roundtrip_json(self):
        ctx = ProjectContext(
            project_name="Orsted TW",
            project_code="ORS-TW",
            client="Orsted",
            vessel="MV Explorer",
            crs_epsg=32651,
            paths=ProjectPaths(raw_data="/data/raw"),
            metadata={"custom_key": 42},
        )
        j = ctx.to_json()
        ctx2 = ProjectContext.from_json(j)
        assert ctx2.project_name == "Orsted TW"
        assert ctx2.project_code == "ORS-TW"
        assert ctx2.client == "Orsted"
        assert ctx2.paths.raw_data == "/data/raw"
        assert ctx2.metadata["custom_key"] == 42

    def test_roundtrip_dict(self):
        ctx = ProjectContext(project_name="Test", vessel_config_id=5)
        d = ctx.to_dict()
        ctx2 = ProjectContext.from_dict(d)
        assert ctx2.project_name == "Test"
        assert ctx2.vessel_config_id == 5

    def test_from_dict_ignores_unknown(self):
        ctx = ProjectContext.from_dict({"project_name": "X", "unknown": True})
        assert ctx.project_name == "X"

    def test_save_and_load_file(self, tmp_path):
        ctx = ProjectContext(project_name="FileTest", project_code="FT-01")
        f = tmp_path / "test.json"
        ctx.save_to_file(f)
        assert f.exists()

        ctx2 = ProjectContext.from_file(f)
        assert ctx2.project_name == "FileTest"
        assert ctx2.project_code == "FT-01"

    def test_from_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            ProjectContext.from_file("/nonexistent/file.json")

    def test_touch_updated(self):
        ctx = ProjectContext()
        old = ctx.updated_at
        import time
        time.sleep(0.01)
        ctx.touch_updated()
        assert ctx.updated_at >= old

    def test_validate_paths(self):
        ctx = ProjectContext(
            paths=ProjectPaths(raw_data="/nonexistent/abc")
        )
        warns = ctx.validate_paths()
        assert len(warns) == 1
