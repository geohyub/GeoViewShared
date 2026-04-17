"""Regression tests for Qt plugin path auto-registration.

PyInstaller one-folder builds and machines with multiple PySide6
installs occasionally fail to locate the Qt platforms plugin, printing
the dreaded "no Qt platform plugin could be initialized" error at
launch. `runtime.register_qt_plugin_paths()` front-runs that
by calling QCoreApplication.addLibraryPath() for the plugins
directory bundled with the running PySide6 binding.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_SHARED_ROOT = str(Path(__file__).resolve().parents[1])
if _SHARED_ROOT not in sys.path:
    sys.path.insert(0, _SHARED_ROOT)

import PySide6
from PySide6.QtCore import QCoreApplication

from geoview_pyside6 import runtime


def test_candidate_dirs_include_pyside_plugins():
    pyside_dir = Path(PySide6.__file__).resolve().parent
    candidates = runtime._candidate_plugin_dirs()
    # At least one candidate must live under the active PySide6 install.
    assert any(
        Path(c).resolve().is_relative_to(pyside_dir)
        for c in candidates
    ), (
        f"No candidate plugin dir under {pyside_dir} was discovered. "
        f"Got: {candidates}"
    )


def test_register_qt_plugin_paths_is_idempotent():
    # First call may or may not add paths (import-time call probably
    # already added them). Second call without force must be a no-op.
    runtime._QT_PLUGIN_PATHS_REGISTERED = True
    added = runtime.register_qt_plugin_paths()
    assert added == [], "Idempotent call added paths a second time"


def test_force_re_registration_returns_added_dirs_if_any():
    # With force=True we re-scan; any dir not already in libraryPaths()
    # is added again. On a standard machine, all plugin dirs are already
    # registered so added may be empty — the test just asserts the call
    # runs cleanly and returns a list.
    before = list(QCoreApplication.libraryPaths())
    added = runtime.register_qt_plugin_paths(force=True)
    after = list(QCoreApplication.libraryPaths())
    assert isinstance(added, list)
    assert len(after) >= len(before), (
        "libraryPaths() shrank after register_qt_plugin_paths(force=True)"
    )


def test_env_override_is_respected(monkeypatch, tmp_path):
    # Operator override via QT_PLUGIN_PATH env. Create a fake dir and
    # check it shows up in candidates when the env var points at it.
    fake = tmp_path / "qt_override"
    fake.mkdir()
    monkeypatch.setenv("QT_PLUGIN_PATH", str(fake))
    candidates = runtime._candidate_plugin_dirs()
    assert any(Path(c).resolve() == fake.resolve() for c in candidates), (
        f"QT_PLUGIN_PATH override {fake} not picked up. Candidates: {candidates}"
    )


def test_invalid_env_override_is_skipped(monkeypatch, tmp_path):
    bogus = tmp_path / "does_not_exist"
    monkeypatch.setenv("QT_PLUGIN_PATH", str(bogus))
    candidates = runtime._candidate_plugin_dirs()
    assert str(bogus) not in candidates, (
        "Nonexistent directory leaked into candidates — is_dir() guard broken"
    )
