"""
geoview_pyside6.build_harness
================================
PyInstaller spec factory + version stamping (Phase A-1 A1.7).

Provides the pieces every GeoView desktop app uses to produce a
distributable Windows build:

 - :class:`PyInstallerConfig` + :func:`make_spec_text` / :func:`write_spec`
   produce a fully-formed PyInstaller ``.spec`` file tuned for GeoView
   conventions (onedir, windowed, Pretendard + Qt plugins bundled).
 - :class:`VersionInfo` + :func:`stamp_version_py` / :func:`stamp_version_rc`
   generate ``_version.py`` and the Windows ``VERSIONINFO`` resource
   PyInstaller embeds in the final EXE (SeismicQC 교훈 #13 — always
   stamp the build with git SHA + ISO time so bug reports are tractable).
 - :func:`read_git_sha` reads ``HEAD`` without shelling out when the
   repo is clean, falling back to ``git rev-parse --short HEAD`` when
   needed.

Scope note (A1.7 is an "S" epic):
 - We **do not** run PyInstaller. That lives in app-level CI. This module
   only generates the inputs.
 - Tests assert the generated files are well-formed and parseable; they
   do not call PyInstaller itself.
"""
from __future__ import annotations

from geoview_pyside6.build_harness.pyinstaller_preset import (
    PyInstallerConfig,
    make_spec_text,
    write_spec,
)
from geoview_pyside6.build_harness.version_stamp import (
    VersionInfo,
    read_git_sha,
    stamp_version_py,
    stamp_version_rc,
)

__all__ = [
    "PyInstallerConfig",
    "make_spec_text",
    "write_spec",
    "VersionInfo",
    "read_git_sha",
    "stamp_version_py",
    "stamp_version_rc",
]
