"""Tests for geoview_pyside6.io_safe.atomic — Phase A-1 A1.3."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from geoview_pyside6.io_safe import (
    UserDataGuardError,
    assert_within_roots,
    atomic_write_bytes,
    atomic_write_text,
    atomic_writer,
    is_within,
    safe_rmdir,
    safe_rmtree,
    safe_unlink,
)


# ---------------------------------------------------------------------------
# Path predicates
# ---------------------------------------------------------------------------


class TestIsWithin:
    def test_child_is_within(self, tmp_path):
        child = tmp_path / "a" / "b.txt"
        child.parent.mkdir()
        child.touch()
        assert is_within(child, tmp_path) is True

    def test_sibling_is_not_within(self, tmp_path):
        a = tmp_path / "a"
        b = tmp_path / "b"
        a.mkdir()
        b.mkdir()
        assert is_within(b, a) is False

    def test_same_path_is_within(self, tmp_path):
        assert is_within(tmp_path, tmp_path) is True


class TestAssertWithinRoots:
    def test_accepts_child(self, tmp_path):
        child = tmp_path / "x"
        child.mkdir()
        resolved = assert_within_roots(child, [tmp_path])
        assert resolved == Path(os.path.realpath(child))

    def test_rejects_outside(self, tmp_path):
        other = tmp_path.parent
        with pytest.raises(UserDataGuardError, match="escapes"):
            assert_within_roots(other, [tmp_path])

    def test_empty_roots_rejected(self, tmp_path):
        with pytest.raises(UserDataGuardError, match="no temp roots"):
            assert_within_roots(tmp_path, [])


# ---------------------------------------------------------------------------
# Atomic write — happy paths
# ---------------------------------------------------------------------------


class TestAtomicWriteBytes:
    def test_creates_file(self, tmp_path):
        target = tmp_path / "out.bin"
        atomic_write_bytes(target, b"hello")
        assert target.read_bytes() == b"hello"

    def test_overwrites_existing(self, tmp_path):
        target = tmp_path / "out.bin"
        target.write_bytes(b"old")
        atomic_write_bytes(target, b"new")
        assert target.read_bytes() == b"new"

    def test_rejects_non_bytes(self, tmp_path):
        with pytest.raises(TypeError):
            atomic_write_bytes(tmp_path / "x", "string")  # type: ignore[arg-type]

    def test_missing_parent_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            atomic_write_bytes(tmp_path / "nope" / "x.bin", b"data")

    def test_no_tmp_files_left_behind(self, tmp_path):
        target = tmp_path / "out.bin"
        atomic_write_bytes(target, b"payload")
        leftovers = [p for p in tmp_path.iterdir() if p.suffix == ".tmp"]
        assert leftovers == []


class TestAtomicWriteText:
    def test_creates_file(self, tmp_path):
        target = tmp_path / "out.txt"
        atomic_write_text(target, "hello ✓")
        assert target.read_text(encoding="utf-8") == "hello ✓"

    def test_custom_encoding(self, tmp_path):
        target = tmp_path / "out.txt"
        atomic_write_text(target, "héllo", encoding="latin-1")
        assert target.read_bytes() == "héllo".encode("latin-1")

    def test_rejects_bytes(self, tmp_path):
        with pytest.raises(TypeError):
            atomic_write_text(tmp_path / "x", b"bytes")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Atomic write — rollback
# ---------------------------------------------------------------------------


class TestAtomicWriterRollback:
    def test_exception_leaves_target_untouched(self, tmp_path):
        target = tmp_path / "out.bin"
        target.write_bytes(b"original")

        class Boom(Exception):
            pass

        with pytest.raises(Boom):
            with atomic_writer(target) as fh:
                fh.write(b"halfway...")
                raise Boom()

        # target content unchanged
        assert target.read_bytes() == b"original"
        # no temp leftovers
        leftovers = [p for p in tmp_path.iterdir() if p.suffix == ".tmp"]
        assert leftovers == []

    def test_exception_on_new_target_leaves_nothing(self, tmp_path):
        target = tmp_path / "out.bin"
        with pytest.raises(RuntimeError):
            with atomic_writer(target) as fh:
                fh.write(b"x")
                raise RuntimeError("boom")
        assert not target.exists()
        assert list(tmp_path.iterdir()) == []

    def test_invalid_mode_rejected(self, tmp_path):
        with pytest.raises(ValueError, match="wb"):
            with atomic_writer(tmp_path / "x", mode="a"):
                pass


# ---------------------------------------------------------------------------
# safe_unlink
# ---------------------------------------------------------------------------


class TestSafeUnlink:
    def test_removes_file(self, tmp_path):
        f = tmp_path / "x.txt"
        f.write_text("hi")
        safe_unlink(f)
        assert not f.exists()

    def test_missing_path_is_idempotent(self, tmp_path):
        safe_unlink(tmp_path / "nope")  # no raise

    def test_directory_refused(self, tmp_path):
        d = tmp_path / "d"
        d.mkdir()
        with pytest.raises(UserDataGuardError, match="refuses directories"):
            safe_unlink(d)

    @pytest.mark.skipif(
        sys.platform == "win32",
        reason="symlink creation requires admin on Windows",
    )
    def test_symlink_removed_not_followed(self, tmp_path):
        target_dir = tmp_path / "real"
        target_dir.mkdir()
        (target_dir / "keeper.txt").write_text("alive")
        link = tmp_path / "link"
        os.symlink(target_dir, link)

        safe_unlink(link)

        assert not link.exists()
        assert (target_dir / "keeper.txt").exists()  # target untouched


# ---------------------------------------------------------------------------
# safe_rmdir
# ---------------------------------------------------------------------------


class TestSafeRmdir:
    def test_removes_empty_dir(self, tmp_path):
        d = tmp_path / "d"
        d.mkdir()
        safe_rmdir(d)
        assert not d.exists()

    def test_non_empty_refused(self, tmp_path):
        d = tmp_path / "d"
        d.mkdir()
        (d / "keep.txt").write_text("x")
        with pytest.raises(UserDataGuardError, match="not empty"):
            safe_rmdir(d)
        assert (d / "keep.txt").exists()

    def test_missing_is_idempotent(self, tmp_path):
        safe_rmdir(tmp_path / "nope")

    def test_file_refused(self, tmp_path):
        f = tmp_path / "x.txt"
        f.write_text("hi")
        with pytest.raises(UserDataGuardError, match="not a directory"):
            safe_rmdir(f)


# ---------------------------------------------------------------------------
# safe_rmtree — the critical guard
# ---------------------------------------------------------------------------


class TestSafeRmtree:
    def test_removes_dir_inside_root(self, tmp_path):
        root = tmp_path / "tmp_root"
        root.mkdir()
        victim = root / "build"
        (victim / "sub").mkdir(parents=True)
        (victim / "file.txt").write_text("x")

        safe_rmtree(victim, temp_roots=[root])

        assert not victim.exists()
        assert root.exists()

    def test_refuses_outside_root(self, tmp_path):
        root = tmp_path / "tmp_root"
        root.mkdir()
        outside = tmp_path / "user_data"
        outside.mkdir()
        (outside / "precious.txt").write_text("data")

        with pytest.raises(UserDataGuardError, match="escapes"):
            safe_rmtree(outside, temp_roots=[root])

        assert (outside / "precious.txt").exists()

    def test_refuses_root_itself(self, tmp_path):
        root = tmp_path / "tmp_root"
        root.mkdir()
        (root / "keep.txt").write_text("x")
        with pytest.raises(UserDataGuardError, match="temp root itself"):
            safe_rmtree(root, temp_roots=[root])
        assert (root / "keep.txt").exists()

    def test_missing_is_idempotent(self, tmp_path):
        root = tmp_path / "tmp_root"
        root.mkdir()
        safe_rmtree(root / "never_existed", temp_roots=[root])

    def test_file_target_refused(self, tmp_path):
        root = tmp_path / "tmp_root"
        root.mkdir()
        f = root / "x.txt"
        f.write_text("x")
        with pytest.raises(UserDataGuardError, match="not a directory"):
            safe_rmtree(f, temp_roots=[root])

    def test_empty_roots_refused(self, tmp_path):
        d = tmp_path / "d"
        d.mkdir()
        with pytest.raises(UserDataGuardError):
            safe_rmtree(d, temp_roots=[])

    @pytest.mark.skipif(
        sys.platform == "win32",
        reason="symlink creation requires admin on Windows",
    )
    def test_refuses_symlink_even_inside_root(self, tmp_path):
        """The cotidal scenario: a symlink inside temp_roots pointing at user data."""
        root = tmp_path / "tmp_root"
        root.mkdir()
        user_data = tmp_path / "precious"
        user_data.mkdir()
        (user_data / "NC_001.nc").write_text("irreplaceable")
        link = root / "shortcut"
        os.symlink(user_data, link)

        with pytest.raises(UserDataGuardError, match="symlinks"):
            safe_rmtree(link, temp_roots=[root])

        # User data still intact — the whole point of the guard.
        assert (user_data / "NC_001.nc").read_text() == "irreplaceable"
