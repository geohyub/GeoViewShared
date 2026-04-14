"""Tests for geoview_pyside6.build_harness.pyinstaller_preset — Phase A-1 A1.7."""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from geoview_pyside6.build_harness.pyinstaller_preset import (
    DEFAULT_DATAS,
    DEFAULT_HIDDEN_IMPORTS,
    PyInstallerConfig,
    make_spec_text,
    write_spec,
)


# ---------------------------------------------------------------------------
# Config validation
# ---------------------------------------------------------------------------


class TestPyInstallerConfig:
    def test_minimal(self):
        cfg = PyInstallerConfig(app_name="X", entry_script="main.py")
        assert cfg.console is False
        assert cfg.onefile is False

    def test_empty_app_name_rejected(self):
        with pytest.raises(ValueError):
            PyInstallerConfig(app_name="", entry_script="main.py")

    def test_reserved_char_rejected(self):
        with pytest.raises(ValueError):
            PyInstallerConfig(app_name="bad?name", entry_script="main.py")

    def test_default_constants_populated(self):
        assert len(DEFAULT_HIDDEN_IMPORTS) > 0
        assert any("pyqtgraph" in h for h in DEFAULT_HIDDEN_IMPORTS)
        assert any("matplotlib" in h for h in DEFAULT_HIDDEN_IMPORTS)
        assert any("openpyxl" in h for h in DEFAULT_HIDDEN_IMPORTS)
        assert len(DEFAULT_DATAS) > 0


# ---------------------------------------------------------------------------
# make_spec_text
# ---------------------------------------------------------------------------


class TestMakeSpecText:
    def test_produces_valid_python(self):
        cfg = PyInstallerConfig(app_name="DummyApp", entry_script="main.py")
        body = make_spec_text(cfg)
        # .spec files are valid Python — parse to catch template typos
        ast.parse(body)

    def test_contains_analysis_and_exe(self):
        cfg = PyInstallerConfig(app_name="DummyApp", entry_script="main.py")
        body = make_spec_text(cfg)
        assert "Analysis(" in body
        assert "PYZ(" in body
        assert "EXE(" in body

    def test_onedir_has_collect_block(self):
        cfg = PyInstallerConfig(app_name="X", entry_script="main.py", onefile=False)
        body = make_spec_text(cfg)
        assert "COLLECT(" in body
        assert "exclude_binaries=True" in body

    def test_onefile_has_no_collect_block(self):
        cfg = PyInstallerConfig(app_name="X", entry_script="main.py", onefile=True)
        body = make_spec_text(cfg)
        assert "COLLECT(" not in body
        assert "a.binaries," in body

    def test_console_flag_honored(self):
        windowed = make_spec_text(
            PyInstallerConfig(app_name="X", entry_script="m.py", console=False)
        )
        console = make_spec_text(
            PyInstallerConfig(app_name="X", entry_script="m.py", console=True)
        )
        assert "console=False" in windowed
        assert "console=True" in console

    def test_icon_line_injected(self):
        cfg = PyInstallerConfig(
            app_name="X", entry_script="m.py", icon_path="assets/app.ico"
        )
        body = make_spec_text(cfg)
        assert "icon='assets/app.ico'" in body

    def test_version_line_injected(self):
        cfg = PyInstallerConfig(
            app_name="X", entry_script="m.py", version_file="version_info.txt"
        )
        body = make_spec_text(cfg)
        assert "version='version_info.txt'" in body

    def test_extras_appended(self):
        cfg = PyInstallerConfig(
            app_name="X",
            entry_script="m.py",
            extra_datas=(("assets/icons", "icons"),),
            extra_hidden_imports=("custom.module",),
        )
        body = make_spec_text(cfg)
        assert "('assets/icons', 'icons')" in body
        assert "'custom.module'" in body

    def test_defaults_included(self):
        cfg = PyInstallerConfig(app_name="X", entry_script="m.py")
        body = make_spec_text(cfg)
        # At least one of each default should appear
        assert "pyqtgraph.exporters" in body
        assert "geoview_pyside6/fonts" in body

    def test_extras_dedup(self):
        cfg = PyInstallerConfig(
            app_name="X",
            entry_script="m.py",
            extra_hidden_imports=(
                "pyqtgraph.exporters",  # already in DEFAULT
                "new.one",
            ),
        )
        body = make_spec_text(cfg)
        # exporter should not appear twice inside the hiddenimports list
        start = body.index("hiddenimports=")
        end = body.index(",\n", start)
        section = body[start:end]
        assert section.count("'pyqtgraph.exporters'") == 1
        assert "'new.one'" in section


# ---------------------------------------------------------------------------
# write_spec
# ---------------------------------------------------------------------------


class TestWriteSpec:
    def test_writes_to_path(self, tmp_path):
        cfg = PyInstallerConfig(app_name="X", entry_script="main.py")
        out = write_spec(cfg, tmp_path / "x.spec")
        assert out.exists()
        ast.parse(out.read_text(encoding="utf-8"))

    def test_creates_parent(self, tmp_path):
        cfg = PyInstallerConfig(app_name="X", entry_script="main.py")
        out = write_spec(cfg, tmp_path / "nested" / "dir" / "x.spec")
        assert out.exists()
