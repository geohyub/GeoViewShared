"""
geoview_pyside6.build_harness.version_stamp
================================================
Build metadata stamping.

Two output forms:

 1. ``_version.py`` — a pure-Python module that imports cheaply. Every
    app reads this at startup and displays the version string in its
    title bar / About dialog (SeismicQC 교훈 #13 — "always stamp the
    build so I can correlate a bug report with a specific commit").

 2. ``version_info.txt`` — PyInstaller's ``VERSIONINFO`` structure that
    ends up embedded in the Windows EXE's resource section. Users who
    right-click → Properties see the real version number; Windows
    Update Services and antivirus tools inspect the same fields.

``read_git_sha`` keeps the git dependency soft: it tries to read
``.git/HEAD`` directly first, falls back to ``git rev-parse --short``,
and returns ``"unknown"`` if both fail (so stamping never blocks a
build on a repo-less source tree).
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from geoview_pyside6.io_safe import atomic_write_text

__all__ = [
    "VersionInfo",
    "read_git_sha",
    "stamp_version_py",
    "stamp_version_rc",
]


_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+(?:[-.+][\w.-]+)?$")


@dataclass(frozen=True)
class VersionInfo:
    """Build metadata stamped into ``_version.py`` / ``version_info.txt``."""

    app_name: str
    version: str                 # semver-ish, e.g. "1.4.2" or "1.4.2-beta.3"
    git_sha: str = "unknown"
    build_time: str = ""         # ISO-8601 UTC; filled on construction
    python_version: str = ""     # filled on construction
    author: str = "Geoview Co., Ltd."
    description: str = ""
    copyright: str = ""

    def __post_init__(self) -> None:
        if not self.app_name:
            raise ValueError("VersionInfo.app_name must not be empty")
        if not _VERSION_RE.match(self.version):
            raise ValueError(
                f"VersionInfo.version must be semver-ish, got {self.version!r}"
            )
        if not self.build_time:
            object.__setattr__(
                self,
                "build_time",
                datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            )
        if not self.python_version:
            object.__setattr__(
                self,
                "python_version",
                ".".join(str(p) for p in sys.version_info[:3]),
            )
        if not self.copyright:
            year = datetime.now(timezone.utc).year
            object.__setattr__(self, "copyright", f"© {year} {self.author}")

    # ------------------------------------------------------------------

    @property
    def version_tuple(self) -> tuple[int, int, int, int]:
        """Windows VERSIONINFO wants a 4-tuple of ints (no pre-release tags)."""
        base = self.version.split("-", 1)[0].split("+", 1)[0]
        parts = [int(p) for p in base.split(".")]
        while len(parts) < 4:
            parts.append(0)
        return (parts[0], parts[1], parts[2], parts[3])


# ---------------------------------------------------------------------------
# git SHA lookup
# ---------------------------------------------------------------------------


def read_git_sha(repo_root: Path | str = ".", *, short: bool = True) -> str:
    """
    Return the current git commit SHA, or ``"unknown"`` on any failure.

    Tries the filesystem first (fast, no subprocess) and only falls back
    to ``git rev-parse`` when the repo is in a packed-ref or detached state.
    """
    root = Path(repo_root)
    head = root / ".git" / "HEAD"
    try:
        if head.exists():
            content = head.read_text(encoding="utf-8").strip()
            if content.startswith("ref:"):
                ref = content.split(" ", 1)[1].strip()
                ref_path = root / ".git" / ref
                if ref_path.exists():
                    sha = ref_path.read_text(encoding="utf-8").strip()
                    return sha[:7] if short else sha
            elif len(content) >= 7 and all(c in "0123456789abcdef" for c in content.lower()):
                return content[:7] if short else content
    except OSError:
        pass

    try:
        cmd = ["git", "rev-parse"]
        if short:
            cmd.append("--short")
        cmd.append("HEAD")
        out = subprocess.run(
            cmd,
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass

    return "unknown"


# ---------------------------------------------------------------------------
# _version.py
# ---------------------------------------------------------------------------


_VERSION_PY_TEMPLATE = '''"""\
Auto-generated build metadata — do not edit by hand.

Regenerated by geoview_pyside6.build_harness.version_stamp.stamp_version_py
on every build.
"""
from __future__ import annotations

APP_NAME = {app_name!r}
VERSION = {version!r}
GIT_SHA = {git_sha!r}
BUILD_TIME = {build_time!r}
PYTHON_VERSION = {python_version!r}
AUTHOR = {author!r}
DESCRIPTION = {description!r}
COPYRIGHT = {copyright!r}

VERSION_TUPLE = {version_tuple!r}

__all__ = [
    "APP_NAME",
    "VERSION",
    "GIT_SHA",
    "BUILD_TIME",
    "PYTHON_VERSION",
    "AUTHOR",
    "DESCRIPTION",
    "COPYRIGHT",
    "VERSION_TUPLE",
]
'''


def stamp_version_py(info: VersionInfo, out_path: Path | str) -> Path:
    """Write a ``_version.py`` module next to the app package."""
    body = _VERSION_PY_TEMPLATE.format(
        app_name=info.app_name,
        version=info.version,
        git_sha=info.git_sha,
        build_time=info.build_time,
        python_version=info.python_version,
        author=info.author,
        description=info.description,
        copyright=info.copyright,
        version_tuple=info.version_tuple,
    )
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(out, body, encoding="utf-8")
    return out


# ---------------------------------------------------------------------------
# Windows VERSIONINFO
# ---------------------------------------------------------------------------


_VERSION_RC_TEMPLATE = """\
# Auto-generated Windows VERSIONINFO for PyInstaller —
# regenerated by geoview_pyside6.build_harness.version_stamp.stamp_version_rc.
#
# Pass this file to PyInstaller via:  EXE(..., version={out_name!r}, ...)

VSVersionInfo(
    ffi=FixedFileInfo(
        filevers={version_tuple},
        prodvers={version_tuple},
        mask=0x3f,
        flags=0x0,
        OS=0x40004,
        fileType=0x1,
        subtype=0x0,
        date=(0, 0),
    ),
    kids=[
        StringFileInfo(
            [
                StringTable(
                    '040904B0',
                    [
                        StringStruct('CompanyName', {author!r}),
                        StringStruct('FileDescription', {description!r}),
                        StringStruct('FileVersion', {version!r}),
                        StringStruct('InternalName', {app_name!r}),
                        StringStruct('LegalCopyright', {copyright!r}),
                        StringStruct('OriginalFilename', {original_filename!r}),
                        StringStruct('ProductName', {app_name!r}),
                        StringStruct('ProductVersion', {version!r}),
                        StringStruct('BuildTime', {build_time!r}),
                        StringStruct('GitSHA', {git_sha!r}),
                    ],
                )
            ]
        ),
        VarFileInfo([VarStruct('Translation', [1033, 1200])]),
    ],
)
"""


def stamp_version_rc(info: VersionInfo, out_path: Path | str) -> Path:
    """Write a Windows VERSIONINFO file consumable by PyInstaller's ``EXE``."""
    out = Path(out_path)
    description = info.description or info.app_name
    body = _VERSION_RC_TEMPLATE.format(
        version_tuple=info.version_tuple,
        version=info.version,
        app_name=info.app_name,
        author=info.author,
        description=description,
        copyright=info.copyright,
        build_time=info.build_time,
        git_sha=info.git_sha,
        original_filename=f"{info.app_name}.exe",
        out_name=out.name,
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(out, body, encoding="utf-8")
    return out
