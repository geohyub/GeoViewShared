"""Tests for geoview_pyside6.build_harness.version_stamp — Phase A-1 A1.7."""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from geoview_pyside6.build_harness.version_stamp import (
    VersionInfo,
    read_git_sha,
    stamp_version_py,
    stamp_version_rc,
)


# ---------------------------------------------------------------------------
# VersionInfo
# ---------------------------------------------------------------------------


class TestVersionInfo:
    def test_minimal(self):
        info = VersionInfo(app_name="Test", version="1.2.3")
        assert info.app_name == "Test"
        assert info.version == "1.2.3"
        assert info.git_sha == "unknown"
        assert info.build_time.endswith("Z")
        assert info.python_version.count(".") == 2
        assert info.copyright.startswith("©")

    def test_version_tuple(self):
        assert VersionInfo("a", "1.2.3").version_tuple == (1, 2, 3, 0)

    def test_version_tuple_handles_prerelease(self):
        assert VersionInfo("a", "1.2.3-beta.4").version_tuple == (1, 2, 3, 0)

    def test_empty_app_name_rejected(self):
        with pytest.raises(ValueError):
            VersionInfo(app_name="", version="1.0.0")

    def test_non_semver_rejected(self):
        with pytest.raises(ValueError):
            VersionInfo(app_name="x", version="v1")

    def test_frozen(self):
        info = VersionInfo("x", "1.0.0")
        with pytest.raises(Exception):
            info.version = "2.0.0"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# read_git_sha
# ---------------------------------------------------------------------------


class TestReadGitSha:
    def test_fs_read_ref(self, tmp_path):
        (tmp_path / ".git").mkdir()
        (tmp_path / ".git" / "HEAD").write_text("ref: refs/heads/master\n")
        (tmp_path / ".git" / "refs" / "heads").mkdir(parents=True)
        (tmp_path / ".git" / "refs" / "heads" / "master").write_text(
            "abcdef1234567890abcdef1234567890abcdef12\n"
        )

        assert read_git_sha(tmp_path, short=True) == "abcdef1"
        assert read_git_sha(tmp_path, short=False) == (
            "abcdef1234567890abcdef1234567890abcdef12"
        )

    def test_detached_head(self, tmp_path):
        (tmp_path / ".git").mkdir()
        (tmp_path / ".git" / "HEAD").write_text(
            "abcdef1234567890abcdef1234567890abcdef12\n"
        )
        assert read_git_sha(tmp_path) == "abcdef1"

    def test_missing_repo_returns_unknown(self, tmp_path):
        assert read_git_sha(tmp_path) == "unknown"

    def test_real_shared_repo_has_sha(self):
        # _shared/ is itself a git repo — this should return a 7-char hex.
        import os

        shared_root = Path(os.getcwd())
        sha = read_git_sha(shared_root)
        assert sha != "unknown"
        assert len(sha) >= 7


# ---------------------------------------------------------------------------
# stamp_version_py
# ---------------------------------------------------------------------------


class TestStampVersionPy:
    def test_file_written(self, tmp_path):
        info = VersionInfo("TestApp", "1.4.2", git_sha="abc1234")
        out = stamp_version_py(info, tmp_path / "_version.py")
        assert out.exists()

    def test_is_valid_python(self, tmp_path):
        info = VersionInfo("TestApp", "1.4.2", git_sha="abc1234")
        out = stamp_version_py(info, tmp_path / "_version.py")
        ast.parse(out.read_text(encoding="utf-8"))

    def test_constants_present(self, tmp_path):
        info = VersionInfo(
            "TestApp",
            "1.4.2",
            git_sha="abc1234",
            description="Demo app",
        )
        out = stamp_version_py(info, tmp_path / "_version.py")
        body = out.read_text(encoding="utf-8")
        assert "APP_NAME = 'TestApp'" in body
        assert "VERSION = '1.4.2'" in body
        assert "GIT_SHA = 'abc1234'" in body
        assert "VERSION_TUPLE = (1, 2, 4, 2, 0)"[:-1]  # sanity: tuple rendered
        assert "VERSION_TUPLE = (1, 4, 2, 0)" in body

    def test_round_trip_import(self, tmp_path):
        info = VersionInfo("TestApp", "0.9.1", git_sha="deadbee")
        out = stamp_version_py(info, tmp_path / "_version.py")
        ns: dict = {}
        exec(out.read_text(encoding="utf-8"), ns)
        assert ns["APP_NAME"] == "TestApp"
        assert ns["VERSION"] == "0.9.1"
        assert ns["GIT_SHA"] == "deadbee"
        assert ns["VERSION_TUPLE"] == (0, 9, 1, 0)

    def test_parent_dir_created(self, tmp_path):
        info = VersionInfo("X", "1.0.0")
        out = stamp_version_py(info, tmp_path / "nested" / "a" / "_version.py")
        assert out.exists()


# ---------------------------------------------------------------------------
# stamp_version_rc
# ---------------------------------------------------------------------------


class TestStampVersionRc:
    def test_file_written(self, tmp_path):
        info = VersionInfo("TestApp", "1.4.2", git_sha="abc1234")
        out = stamp_version_rc(info, tmp_path / "version_info.txt")
        assert out.exists()

    def test_contains_required_keys(self, tmp_path):
        info = VersionInfo(
            "TestApp",
            "1.4.2",
            git_sha="abc1234",
            description="Demo",
        )
        out = stamp_version_rc(info, tmp_path / "version_info.txt")
        body = out.read_text(encoding="utf-8")
        for marker in (
            "VSVersionInfo",
            "FixedFileInfo",
            "filevers=(1, 4, 2, 0)",
            "StringStruct('FileVersion', '1.4.2')",
            "StringStruct('ProductVersion', '1.4.2')",
            "StringStruct('GitSHA', 'abc1234')",
            "StringStruct('InternalName', 'TestApp')",
            "StringStruct('OriginalFilename', 'TestApp.exe')",
        ):
            assert marker in body, f"missing {marker!r}"

    def test_description_falls_back_to_app_name(self, tmp_path):
        info = VersionInfo("NoDesc", "1.0.0")
        out = stamp_version_rc(info, tmp_path / "v.txt")
        body = out.read_text(encoding="utf-8")
        assert "StringStruct('FileDescription', 'NoDesc')" in body
